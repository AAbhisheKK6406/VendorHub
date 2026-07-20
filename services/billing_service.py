from datetime import datetime
import mysql.connector
from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

# ==========================================
# 1. NEW DASHBOARD & REPORTING HELPERS
# ==========================================

def get_recent_bills(vendor_id, limit=5):
    """
    Read-only helper to populate a high-performance 'Recent Transactions' UI table.
    Uses a shallow join to avoid the resource-heavy payload of full invoice generation.
    """
    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "bills": []}

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT s.sale_id, s.bill_number, s.sale_date, s.total_amount, s.payment_status,
                   c.customer_name 
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.vendor_id = %s 
            ORDER BY s.sale_id DESC 
            LIMIT %s
        """
        cursor.execute(query, (vendor_id, int(limit)))
        records = cursor.fetchall()
        
        # Format dates cleanly for frontend consumption
        for r in records:
            if r['sale_date']:
                r['sale_date'] = r['sale_date'].strftime("%Y-%m-%d %H:%M:%S")

        return {"success": True, "bills": records}
    except mysql.connector.Error as db_error:
        return {"success": False, "message": f"Metrics query failed: {db_error}", "bills": []}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)


def get_billing_dashboard_data(vendor_id):
    """
    Aggregates all billing metrics, payment states, time windows, and 
    recent transactions in a single database execution block.
    """
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "data": None}

    try:
        cursor = connection.cursor(dictionary=True)
        dashboard_payload = {}

        # 1. Gather ALL Aggregate Snapshot Values (Your logic + Time window logic)
        metrics_query = """
            SELECT 
                COUNT(sale_id) as total_bills,
                COUNT(CASE WHEN payment_status = 'Paid' THEN 1 END) as settled_invoices_count,
                COALESCE(SUM(CASE WHEN payment_status = 'Paid' THEN total_amount END), 0.00) as gross_revenue,
                COALESCE(SUM(CASE WHEN payment_status != 'Paid' THEN total_amount END), 0.00) as pending_receivables,
                COALESCE(SUM(CASE WHEN DATE(sale_date) = CURDATE() THEN total_amount ELSE 0 END), 0.0) as today_sales,
                COALESCE(SUM(CASE WHEN sale_date >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN total_amount ELSE 0 END), 0.0) as monthly_revenue
            FROM sales
            WHERE vendor_id = %s
        """
        cursor.execute(metrics_query, (vendor_id,))
        aggregates = cursor.fetchone()

        # Build out the metrics payload dictionary
        dashboard_payload["total_bills"] = int(aggregates["total_bills"]) if aggregates else 0
        dashboard_payload["settled_invoices"] = int(aggregates["settled_invoices_count"]) if aggregates else 0
        dashboard_payload["gross_revenue"] = round(float(aggregates["gross_revenue"]), 2) if aggregates else 0.0
        dashboard_payload["pending_receivables"] = round(float(aggregates["pending_receivables"]), 2) if aggregates else 0.0
        dashboard_payload["today_sales"] = round(float(aggregates["today_sales"]), 2) if aggregates else 0.0
        dashboard_payload["monthly_revenue"] = round(float(aggregates["monthly_revenue"]), 2) if aggregates else 0.0

        # 2. Extract Top 5 Recent Transaction Records for the table widget
        recent_query = """
            SELECT 
                s.sale_id,
                COALESCE(c.customer_name, 'Walk-in Customer') as customer_name,
                s.total_amount,
                s.payment_status,
                s.sale_date
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.vendor_id = %s
            ORDER BY s.sale_date DESC, s.sale_id DESC
            LIMIT 5
        """
        cursor.execute(recent_query, (vendor_id,))
        recent_records = cursor.fetchall()

        formatted_recent = []
        for row in recent_records:
            formatted_recent.append({
                "sale_id": int(row["sale_id"]),
                "customer_name": row["customer_name"],
                "total_amount": round(float(row["total_amount"]), 2),
                "payment_status": row["payment_status"],
                "sale_date": row["sale_date"].strftime("%Y-%m-%d %H:%M:%S") if row["sale_date"] else "N/A"
            })

        dashboard_payload["recent_bills"] = formatted_recent

        return {
            "success": True,
            "message": "Billing dashboard operational matrix compiled successfully.",
            "data": dashboard_payload
        }

    except Error as db_error:
        return {"success": False, "message": f"Database financial extraction failure: {db_error}", "data": None}
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)


# ==========================================
# 2. OPTIMIZED TRANSACTIONAL WORKFLOWS
# ==========================================

def create_bill(vendor_id, customer_id):
    if not vendor_id or not customer_id:
        return {"success": False, "message": "Validation Failure: IDs mandatory.", "bill_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database offline.", "bill_data": None}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        customer_check_query = "SELECT customer_name FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(customer_check_query, (customer_id, vendor_id))
        if not cursor.fetchone():
            connection.rollback()
            return {"success": False, "message": "Security Alert: Access denied.", "bill_data": None}

        latest_bill_query = "SELECT bill_number FROM sales WHERE vendor_id = %s ORDER BY sale_id DESC LIMIT 1"
        cursor.execute(latest_bill_query, (vendor_id,))
        last_bill_record = cursor.fetchone()

        next_numeric_id = 1
        if last_bill_record and last_bill_record['bill_number']:
            try:
                next_numeric_id = int(last_bill_record['bill_number'].replace("BILL", "")) + 1
            except ValueError:
                next_numeric_id = 1

        new_bill_number = f"BILL{next_numeric_id:06d}"
        current_timestamp = datetime.now()

        insert_header_query = """
            INSERT INTO sales (bill_number, vendor_id, customer_id, sale_date, subtotal, discount, 
                               discount_type, tax, gst_percentage, total_amount, payment_method, payment_status)
            VALUES (%s, %s, %s, %s, 0.00, 0.00, 'fixed', 0.00, 0.00, 0.00, 'Pending', 'Unpaid')
        """
        cursor.execute(insert_header_query, (new_bill_number, vendor_id, customer_id, current_timestamp))
        connection.commit()
        
        return {
            "success": True,
            "message": f"Successfully initialized Bill {new_bill_number}.",
            "bill_data": {
                "sale_id": cursor.lastrowid,
                "bill_number": new_bill_number,
                "customer_id": customer_id,
                "vendor_id": vendor_id,
                "bill_date": current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except mysql.connector.Error as db_error:
        if connection: connection.rollback()
        return {"success": False, "message": f"Database processing failure: {db_error}", "bill_data": None}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)


def add_product_to_bill(sale_id, product_id, requested_quantity):
    """
    UPDATED: Item assignment step ONLY. Stock verification remains present, but the immediate 
    inventory deduction has been removed to prevent double-deduction before payment is complete.
    """
    if requested_quantity <= 0:
        return {"success": False, "message": "Quantity must be greater than zero."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        product_query = "SELECT product_name, selling_price, quantity FROM products WHERE product_id = %s"
        cursor.execute(product_query, (product_id,))
        product = cursor.fetchone()

        if not product:
            connection.rollback()
            return {"success": False, "message": "Product not found."}

        if product['quantity'] < requested_quantity:
            connection.rollback()
            return {"success": False, "message": f"Insufficient available stock. Stock: {product['quantity']}"}

        unit_price = float(product['selling_price'])
        subtotal = unit_price * requested_quantity

        insert_item_query = """
            INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_item_query, (sale_id, product_id, requested_quantity, unit_price, subtotal))
        connection.commit()
        
        return {
            "success": True,
            "message": f"Added {product['product_name']} to bill.",
            "item_details": {"product_id": product_id, "quantity": requested_quantity, "subtotal": subtotal}
        }
    except mysql.connector.Error as db_error:
        if connection: connection.rollback()
        return {"success": False, "message": f"Database failure: {db_error}"}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)


def calculate_bill_total(sale_id, vendor_id, discount_type, discount_value, tax_percentage, payment_method, payment_status):
    if discount_type not in ['fixed', 'percentage'] or discount_value < 0 or tax_percentage < 0:
        return {"success": False, "message": "Invalid calculations bounds parameters.", "bill_summary": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database offline.", "bill_summary": None}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT bill_number FROM sales WHERE sale_id = %s AND vendor_id = %s", (sale_id, vendor_id))
        bill_record = cursor.fetchone()
        if not bill_record:
            connection.rollback()
            return {"success": False, "message": "Access denied.", "bill_summary": None}

        cursor.execute("SELECT quantity, unit_price, subtotal FROM sale_items WHERE sale_id = %s", (sale_id,))
        line_items = cursor.fetchall()

        raw_subtotal = sum(float(item['subtotal']) for item in line_items)
        calculated_discount = raw_subtotal * (float(discount_value) / 100.0) if discount_type == 'percentage' else float(discount_value)
        if calculated_discount > raw_subtotal: calculated_discount = raw_subtotal

        taxable_balance = raw_subtotal - calculated_discount
        calculated_tax = taxable_balance * (float(tax_percentage) / 100.0)
        final_total_amount = round(taxable_balance + calculated_tax, 2)

        update_sales_query = """
            UPDATE sales 
            SET subtotal = %s, discount_type = %s, discount = %s, tax = %s, gst_percentage = %s,
                total_amount = %s, payment_method = %s, payment_status = %s
            WHERE sale_id = %s AND vendor_id = %s
        """
        cursor.execute(update_sales_query, (round(raw_subtotal, 2), discount_type, round(calculated_discount, 2), 
                                           round(calculated_tax, 2), float(tax_percentage), final_total_amount, 
                                           payment_method, payment_status, sale_id, vendor_id))
        connection.commit()
        return {"success": True, "message": "Totals updated.", "bill_summary": {"total_amount": final_total_amount}}
    except mysql.connector.Error as db_error:
        if connection: connection.rollback()
        return {"success": False, "message": f"Database failure: {db_error}", "bill_summary": None}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)


def finalize_bill(sale_id, vendor_id):
    if not sale_id or not vendor_id:
        return {"success": False, "message": "Missing core references.", "bill_summary": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "bill_summary": None}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT bill_number, payment_status, total_amount FROM sales WHERE sale_id = %s AND vendor_id = %s", (sale_id, vendor_id))
        bill_record = cursor.fetchone()

        if not bill_record:
            connection.rollback()
            return {"success": False, "message": "Invoice record missing.", "bill_summary": None}
        if bill_record['payment_status'] == 'Paid':
            connection.rollback()
            return {"success": False, "message": "Invoice already completed.", "bill_summary": None}

        cursor.execute("SELECT COUNT(*) as item_count FROM sale_items WHERE sale_id = %s", (sale_id,))
        if cursor.fetchone()['item_count'] == 0:
            connection.rollback()
            return {"success": False, "message": "Cannot finalize an empty line bill.", "bill_summary": None}

        cursor.execute("UPDATE sales SET payment_status = 'Paid' WHERE sale_id = %s AND vendor_id = %s", (sale_id, vendor_id))
        connection.commit()

        return {
            "success": True,
            "message": f"Finalized Bill {bill_record['bill_number']}.",
            "bill_summary": {"sale_id": sale_id, "payment_status": "Paid"}
        }
    except mysql.connector.Error as db_error:
        if connection: connection.rollback()
        return {"success": False, "message": f"Processing Exception: {db_error}", "bill_summary": None}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)


def update_inventory_after_sale(sale_id, vendor_id):
    """
    UPDATED: Fixed the N+1 pattern bottleneck and double-deduction bug.
    Fetches details and checks stock balances in single-pass operations using localized locks.
    """
    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database offline.", "deduction_summary": None}

    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # 1. State Verification Guard Check
        cursor.execute("SELECT payment_status, bill_number FROM sales WHERE sale_id = %s AND vendor_id = %s", (sale_id, vendor_id))
        bill = cursor.fetchone()
        if not bill or bill['payment_status'] != 'Paid':
            connection.rollback()
            return {"success": False, "message": "Target bill must be explicitly finalized and paid first.", "deduction_summary": None}

        # 2. Single Batch Read of Purchased Quantities
        cursor.execute("SELECT product_id, quantity FROM sale_items WHERE sale_id = %s", (sale_id,))
        purchased_items = cursor.fetchall()
        if not purchased_items:
            connection.rollback()
            return {"success": False, "message": "No lines found.", "deduction_summary": None}

        product_ids = [item['product_id'] for item in purchased_items]
        format_strings = ','.join(['%s'] * len(product_ids))

        # 3. Optimized Block Lock: Row locks all required master stock elements simultaneously
        lock_query = f"SELECT product_id, product_name, quantity FROM products WHERE product_id IN ({format_strings}) AND vendor_id = %s FOR UPDATE"
        cursor.execute(lock_query, tuple(product_ids) + (vendor_id,))
        inventory_records = {row['product_id']: row for row in cursor.fetchall()}

        deducted_items_log = []

        # 4. In-Memory Validation Loop
        for item in purchased_items:
            prod_id = item['product_id']
            qty_sold = int(item['quantity'])

            if prod_id not in inventory_records:
                connection.rollback()
                return {"success": False, "message": f"Inventory Integrity Error: Master entry for ID {prod_id} missing.", "deduction_summary": None}

            product_row = inventory_records[prod_id]
            current_stock = int(product_row['quantity'])

            if current_stock < qty_sold:
                connection.rollback()
                return {"success": False, "message": f"Stockout Failure: '{product_row['product_name']}' has insufficient items ({current_stock}). Transaction aborted.", "deduction_summary": None}

            # 5. Process Sequential Micro-Updates inside memory frame
            cursor.execute("UPDATE products SET quantity = quantity - %s WHERE product_id = %s", (qty_sold, prod_id))
            deducted_items_log.append({"product_id": prod_id, "remaining_stock": current_stock - qty_sold})

        connection.commit()
        return {"success": True, "deduction_summary": {"sale_id": sale_id, "items": deducted_items_log}}

    except mysql.connector.Error as db_error:
        if connection: connection.rollback()
        return {"success": False, "message": f"Database atomic rollback: {db_error}", "deduction_summary": None}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)


def generate_invoice(sale_id, vendor_id):
    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "invoice_data": None}

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM sales WHERE sale_id = %s AND vendor_id = %s", (sale_id, vendor_id))
        bill_record = cursor.fetchone()
        if not bill_record:
            return {"success": False, "message": "Security Alert: Bill reference invalid.", "invoice_data": None}

        cursor.execute("SELECT username, business_name, phone, email FROM vendors WHERE id = %s", (vendor_id,))
        vendor_record = cursor.fetchone()

        # UPDATED: Replaced generic 'except Exception' fallback blocks with specific, targeted KeyError checking logic
        target_customer_id = bill_record['customer_id']
        cursor.execute("SELECT customer_name, phone, email, address FROM customers WHERE customer_id = %s", (target_customer_id,))
        customer_record = cursor.fetchone()

        items_query = """
            SELECT si.product_id, p.product_name, si.quantity, si.unit_price, si.subtotal 
            FROM sale_items si
            LEFT JOIN products p ON si.product_id = p.product_id
            WHERE si.sale_id = %s
        """
        cursor.execute(items_query, (sale_id,))
        items_records = cursor.fetchall()

        product_list = [{
            "product_id": item['product_id'],
            "product_name": item['product_name'] if item['product_name'] else f"Product #{item['product_id']}",
            "quantity": int(item['quantity']),
            "unit_price": float(item['unit_price']),
            "total_line_price": float(item['subtotal'])
        } for item in items_records]

        return {
            "success": True,
            "invoice_data": {
                "vendor_details": {
                    "shop_name": vendor_record["business_name"] if vendor_record else "Vendor Partner",
                    "phone": vendor_record["phone"] if vendor_record else "N/A"
                },
                "customer_details": {
                    "customer_name": customer_record['customer_name'] if customer_record else "Walk-in Customer",
                    "phone": customer_record['phone'] if customer_record else "N/A"
                },
                "bill_details": {
                    "bill_number": bill_record['bill_number'],
                    "date": bill_record['sale_date'].strftime("%Y-%m-%d %H:%M:%S") if bill_record['sale_date'] else "N/A",
                    "status": bill_record['payment_status']
                },
                "products": product_list,
                "financial_summary": {
                    "subtotal": float(bill_record['subtotal']),
                    "grand_total": float(bill_record['total_amount'])
                }
            }
        }
    except mysql.connector.Error as db_error:
        return {"success": False, "message": f"Database system driver failure: {db_error}", "invoice_data": None}
    finally:
        if 'cursor' in locals(): cursor.close()
        close_database_connection(connection)