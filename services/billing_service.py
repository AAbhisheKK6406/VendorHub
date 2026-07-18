from datetime import datetime
import mysql.connector
from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def create_bill(vendor_id, customer_id):
    """
    Initializes a new transaction invoice header (Draft stage) for a specific customer.
    Maps perfectly to the frozen schema including discount_type and gst_percentage.
    
    Args:
        vendor_id (int): The ID of the operating vendor.
        customer_id (int): The ID of the target customer.
        
    Returns:
        dict: Success status, response message, and structured bill metadata layout.
    """
    # 1. Input Validation Guards
    if not vendor_id or not customer_id:
        return {"success": False, "message": "Validation Failure: Vendor ID and Customer ID are mandatory.", "bill_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "bill_data": None}

    try:
        # Start transaction block for financial integrity
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # 2. Security Guard Check: Verify customer multi-tenant access rights
        customer_check_query = "SELECT customer_name FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(customer_check_query, (customer_id, vendor_id))
        customer = cursor.fetchone()

        if not customer:
            connection.rollback()
            return {"success": False, "message": "Security Alert: Customer profile not found or unauthorized.", "bill_data": None}

        # 3. Automated Sequential Bill Number Generation
        latest_bill_query = """
            SELECT bill_number FROM sales 
            WHERE vendor_id = %s 
            ORDER BY sale_id DESC LIMIT 1
        """
        cursor.execute(latest_bill_query, (vendor_id,))
        last_bill_record = cursor.fetchone()

        next_numeric_id = 1
        if last_bill_record and last_bill_record['bill_number']:
            last_bill_str = last_bill_record['bill_number']
            try:
                next_numeric_id = int(last_bill_str.replace("BILL", "")) + 1
            except ValueError:
                next_numeric_id = 1

        new_bill_number = f"BILL{next_numeric_id:06d}"
        current_timestamp = datetime.now()

        # 4. Store Bill Header inside the sales table using every required column
        insert_header_query = """
            INSERT INTO sales (
                bill_number, vendor_id, customer_id, sale_date, 
                subtotal, discount, discount_type, tax, gst_percentage,
                total_amount, payment_method, payment_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        insert_values = (
            new_bill_number, 
            vendor_id, 
            customer_id, 
            current_timestamp, 
            0.00,        # subtotal baseline
            0.00,        # discount baseline
            'fixed',     # discount_type default ruleset
            0.00,        # tax baseline
            0.00,        # gst_percentage baseline
            0.00,        # total_amount baseline
            'Pending',   # payment_method string value
            'Unpaid'     # payment_status baseline state
        )
        
        cursor.execute(insert_header_query, insert_values)
        
        # Commit the transaction block safely
        connection.commit()
        generated_sale_id = cursor.lastrowid

        # 5. Return structured contract response payload
        return {
            "success": True,
            "message": f"Successfully initialized Bill Header {new_bill_number}.",
            "bill_data": {
                "sale_id": generated_sale_id,
                "bill_number": new_bill_number,
                "customer_id": customer_id,
                "vendor_id": vendor_id,
                "bill_date": current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
        }

    except Error as db_error:
        if connection:
            connection.rollback()
        return {"success": False, "message": f"Database transactional processing failure: {db_error}", "bill_data": None}

    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def add_product_to_bill(sale_id, product_id, requested_quantity):
    """
    Validates product availability from the products table, computes line subtotals,
    deducts inventory, and inserts the item into the sale_items table.
    """
    if requested_quantity <= 0:
        return {"success": False, "message": "Quantity must be greater than zero."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # 1. Fetch product details using the correct schema columns: product_id, selling_price, quantity
        product_query = """
            SELECT product_name, selling_price, quantity 
            FROM products 
            WHERE product_id = %s
        """
        cursor.execute(product_query, (product_id,))
        product = cursor.fetchone()

        if not product:
            connection.rollback()
            return {"success": False, "message": "Product not found."}

        # 2. Check stock availability using the correct 'quantity' column
        current_stock = product['quantity']
        if current_stock < requested_quantity:
            connection.rollback()
            return {
                "success": False, 
                "message": f"Insufficient stock. Available: {current_stock}, Requested: {requested_quantity}"
            }

        # 3. Calculate financial subtotals
        unit_price = float(product['selling_price'])
        subtotal = unit_price * requested_quantity

        # 4. Deduct inventory from the products table using correct column names
        update_stock_query = """
            UPDATE products 
            SET quantity = quantity - %s 
            WHERE product_id = %s
        """
        cursor.execute(update_stock_query, (requested_quantity, product_id))

        # 5. Insert line item record into sale_items
        insert_item_query = """
            INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_item_query, (sale_id, product_id, requested_quantity, unit_price, subtotal))

        connection.commit()
        return {
            "success": True,
            "message": f"Successfully added {product['product_name']} to the bill.",
            "item_details": {
                "product_id": product_id,
                "product_name": product['product_name'],
                "quantity": requested_quantity,
                "unit_price": unit_price,
                "subtotal": subtotal
            }
        }

    except Error as db_error:
        if connection:
            connection.rollback()
        return {"success": False, "message": f"Database failure: {db_error}"}

    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def calculate_bill_total(sale_id, vendor_id, discount_type, discount_value, tax_percentage, payment_method, payment_status):
    """
    Computes financial metrics for a bill based on sale_items, applies discounts/tax,
    and updates the main sales ledger table.
    """
    # 1. Input Validation Guards
    if discount_type not in ['fixed', 'percentage']:
        return {"success": False, "message": "Invalid discount type provided.", "bill_summary": None}
    
    if discount_value < 0 or tax_percentage < 0:
        return {"success": False, "message": "Monetary inputs cannot be negative.", "bill_summary": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "bill_summary": None}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # 2. Tenancy Security Guard: Ensure the bill exists and belongs to this vendor
        bill_query = "SELECT bill_number FROM sales WHERE sale_id = %s AND vendor_id = %s"
        cursor.execute(bill_query, (sale_id, vendor_id))
        bill_record = cursor.fetchone()

        if not bill_record:
            connection.rollback()
            return {"success": False, "message": "Security Alert: Bill not found or access denied.", "bill_summary": None}

        bill_number = bill_record['bill_number']

        # 3. Retrieve all items added via add_product_to_bill()
        items_query = "SELECT quantity, unit_price, subtotal FROM sale_items WHERE sale_id = %s"
        cursor.execute(items_query, (sale_id,))
        line_items = cursor.fetchall()

        # 4. Compute Base Totals
        total_products = len(line_items)
        total_quantity = sum(int(item['quantity']) for item in line_items)
        raw_subtotal = sum(float(item['subtotal']) for item in line_items)

        # 5. Apply Discount Engine Logic
        if discount_type == 'percentage':
            calculated_discount = raw_subtotal * (float(discount_value) / 100.0)
        else:
            calculated_discount = float(discount_value)

        # 6. Safety Floor Guard: Discount cannot make the subtotal negative
        if calculated_discount > raw_subtotal:
            calculated_discount = raw_subtotal

        # 7. Post-Discount Tax/GST Calculation
        taxable_balance = raw_subtotal - calculated_discount
        calculated_tax = taxable_balance * (float(tax_percentage) / 100.0)

        # 8. Compute Absolute Grand Total
        final_total_amount = taxable_balance + calculated_tax

        # Format everything cleanly to 2 decimal places
        raw_subtotal = round(raw_subtotal, 2)
        calculated_discount = round(calculated_discount, 2)
        calculated_tax = round(calculated_tax, 2)
        final_total_amount = round(final_total_amount, 2)

        # 9 & 10. Persist changes back to your finalized sales table schema
        update_sales_query = """
            UPDATE sales 
            SET subtotal = %s, 
                discount_type = %s, 
                discount = %s, 
                tax = %s, 
                gst_percentage = %s,
                total_amount = %s, 
                payment_method = %s, 
                payment_status = %s
            WHERE sale_id = %s AND vendor_id = %s
        """
        update_values = (
            raw_subtotal,
            discount_type,
            calculated_discount,
            calculated_tax,
            float(tax_percentage),
            final_total_amount,
            payment_method,
            payment_status,
            sale_id,
            vendor_id
        )
        cursor.execute(update_sales_query, update_values)
        
        connection.commit()

        # 11. Return clean contract payload dictionary
        return {
            "success": True,
            "message": "Bill totals computed and saved successfully.",
            "bill_summary": {
                "sale_id": sale_id,
                "bill_number": bill_number,
                "total_products": total_products,
                "total_quantity": total_quantity,
                "subtotal": raw_subtotal,
                "discount_type": discount_type,
                "discount_value": float(discount_value),
                "discount_amount": calculated_discount,
                "tax_percentage": float(tax_percentage),
                "tax_amount": calculated_tax,
                "total_amount": final_total_amount,
                "payment_method": payment_method,
                "payment_status": payment_status
            }
        }

    except Error as db_error:
        if connection:
            connection.rollback()
        return {"success": False, "message": f"Database failure: {db_error}", "bill_summary": None}

    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)