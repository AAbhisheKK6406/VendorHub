import mysql.connector
from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def add_product(vendor_id, product_name, category, purchase_price, selling_price, quantity=0, low_stock_limit=5, barcode=None):
    """
    Validates and inserts a new product into the database.
    Only allows active vendors to attach items to their inventory.
    
    Returns:
        A dictionary containing 'success' (bool) and 'message' (str).
    """
    # 1. Basic Field Validation (Check if required fields are present)
    if not vendor_id or not product_name or not category:
        return {"success": False, "message": "Missing required fields: Vendor ID, Product Name, and Category are mandatory."}

    # 2. Financial & Quantity Validations
    try:
        # Convert inputs to correct formats to prevent type errors
        purchase_price = float(purchase_price)
        selling_price = float(selling_price)
        quantity = int(quantity)
        low_stock_limit = int(low_stock_limit)
    except (ValueError, TypeError):
        return {"success": False, "message": "Invalid number formatting for prices or quantity."}

    if purchase_price < 0 or selling_price <= 0:
        return {"success": False, "message": "Prices must be logical. Purchase price cannot be negative, and selling price must be greater than 0."}

    if quantity < 0:
        return {"success": False, "message": "Starting inventory quantity cannot be negative."}

    if low_stock_limit < 0:
        return {"success": False, "message": "Low stock threshold limit cannot be negative."}

    # 3. Database Operation
    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database connection offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # Confirm the vendor actually exists before trying to associate a product
        vendor_check_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_check_query, (vendor_id,))
        vendor_exists = cursor.fetchone()

        if not vendor_exists:
            return {"success": False, "message": "Unauthorized operation. Registered vendor not found."}

        # Parameterized INSERT statement to block SQL Injection vulnerabilities
        insert_query = """
            INSERT INTO products (vendor_id, product_name, category, purchase_price, selling_price, quantity, low_stock_limit, barcode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        product_data = (vendor_id, product_name.strip(), category.strip(), purchase_price, selling_price, quantity, low_stock_limit, barcode)
        
        cursor.execute(insert_query, product_data)
        connection.commit()  # Push the changes permanently to MySQL

        return {"success": True, "message": f"Product '{product_name}' successfully added to your inventory!"}

    except Error as db_error:
        return {"success": False, "message": f"Database insertion failure: {db_error}"}

    finally:
        # Clean up database resources
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def view_products(vendor_id):
    """
    Retrieves all products belonging to a specific vendor.
    
    Args:
        vendor_id (int): The unique ID of the logged-in vendor.
        
    Returns:
        dict: A status dictionary containing 'success', 'message', and a 'products' list.
    """
    # 1. Check if the vendor_id is valid
    if not vendor_id:
        return {"success": False, "message": "Invalid Vendor ID provided.", "products": []}

    # 2. Establish database connection
    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database connection offline.", "products": []}

    try:
        # Open a dictionary cursor so columns are mapped to keys automatically
        cursor = connection.cursor(dictionary=True)

        # Secure parameterized SELECT query targeting ONLY this vendor's items
        query = """
            SELECT product_id, product_name, category, purchase_price, 
                   selling_price, quantity, low_stock_limit, barcode 
            FROM products 
            WHERE vendor_id = %s 
            ORDER BY product_id DESC
        """
        
        cursor.execute(query, (vendor_id,))
        products_list = cursor.fetchall() # Fetch all matching records

        # 3. Handle empty state if vendor has no inventory items
        if not products_list:
            return {
                "success": True, 
                "message": "Your inventory is currently empty. Start by adding a product!", 
                "products": []
            }

        return {
            "success": True, 
            "message": f"Successfully retrieved {len(products_list)} products.", 
            "products": products_list
        }

    except Error as db_error:
        return {"success": False, "message": f"Database query failure: {db_error}", "products": []}

    finally:
        # Ensure database cursor and connection objects are closed safely
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def update_product(vendor_id, product_id, product_name=None, category=None, purchase_price=None, selling_price=None, quantity=None, low_stock_limit=None):
    """
    Safely and dynamically updates fields for an existing product.
    Strictly verifies that the target product belongs to the requesting vendor.
    
    Returns:
        dict: Success status and feedback message.
    """
    # 1. Enforce presence of identifying key parameters
    if not vendor_id or not product_id:
        return {"success": False, "message": "Crucial Parameters Missing: Vendor ID and Product ID are mandatory."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Enforce structural isolation boundary check
        check_query = "SELECT product_id FROM products WHERE product_id = %s AND vendor_id = %s"
        cursor.execute(check_query, (product_id, vendor_id))
        target_product = cursor.fetchone()

        if not target_product:
            return {"success": False, "message": "Access Denied: Product not found or unauthorized account access."}

        # 3. Parse and build dynamic SQL components based on input variables
        fields_to_update = []
        execution_values = []

        if product_name is not None:
            fields_to_update.append("product_name = %s")
            execution_values.append(product_name.strip())

        if category is not None:
            fields_to_update.append("category = %s")
            execution_values.append(category.strip())

        if purchase_price is not None:
            price_val = float(purchase_price)
            if price_val < 0:
                return {"success": False, "message": "Validation Failure: Purchase price cannot be negative."}
            fields_to_update.append("purchase_price = %s")
            execution_values.append(price_val)

        if selling_price is not None:
            sell_val = float(selling_price)
            if sell_val <= 0:
                return {"success": False, "message": "Validation Failure: Selling price must be greater than zero."}
            fields_to_update.append("selling_price = %s")
            execution_values.append(sell_val)

        if quantity is not None:
            qty_val = int(quantity)
            if qty_val < 0:
                return {"success": False, "message": "Validation Failure: Quantity cannot be negative."}
            fields_to_update.append("quantity = %s")
            execution_values.append(qty_val)

        if low_stock_limit is not None:
            limit_val = int(low_stock_limit)
            if limit_val < 0:
                return {"success": False, "message": "Validation Failure: Low stock limit cannot be negative."}
            fields_to_update.append("low_stock_limit = %s")
            execution_values.append(limit_val)

        # 4. If no non-None arguments were passed down, stop processing
        if not fields_to_update:
            return {"success": False, "message": "No new parameters provided for modification."}

        # Append tracking reference keys to terminate the execution tuple
        execution_values.extend([product_id, vendor_id])

        # Synthesize final parameterized update query statement text
        sql_update_statement = f"""
            UPDATE products 
            SET {', '.join(fields_to_update)} 
            WHERE product_id = %s AND vendor_id = %s
        """

        cursor.execute(sql_update_statement, tuple(execution_values))
        connection.commit() # Save transactions securely down to server logs

        return {"success": True, "message": "Product attributes updated successfully."}

    except Error as db_error:
        return {"success": False, "message": f"Database processing exception error encountered: {db_error}"}
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def delete_product(vendor_id, product_id):
    """
    Safely deletes a product from the inventory catalog.
    Strictly verifies that the target product exists and belongs to the requesting vendor.
    
    Returns:
        dict: Success status and feedback message.
    """
    # 1. Enforce presence of required tracking parameters
    if not vendor_id or not product_id:
        return {"success": False, "message": "Parameters Missing: Vendor ID and Product ID are mandatory."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Check existence and verify tenant ownership before executing destructive action
        check_query = "SELECT product_id, product_name FROM products WHERE product_id = %s AND vendor_id = %s"
        cursor.execute(check_query, (product_id, vendor_id))
        target_product = cursor.fetchone()

        if not target_product:
            return {"success": False, "message": "Deletion Failed: Product not found or unauthorized access."}

        product_name = target_product['product_name']

        # 3. Execute secure parameterized DELETE query statement
        delete_query = "DELETE FROM products WHERE product_id = %s AND vendor_id = %s"
        cursor.execute(delete_query, (product_id, vendor_id))
        
        connection.commit() # Save transactions securely down to server disks

        return {"success": True, "message": f"Product '{product_name}' (ID: {product_id}) successfully removed from your inventory."}

    except Error as db_error:
        return {"success": False, "message": f"Database processing error during deletion: {db_error}"}
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def search_products(vendor_id, query_text=None, category=None, product_id=None, barcode=None):
    """
    Dynamically filters and searches the vendor's inventory catalog.
    Supports partial lookups for names/categories and exact matches for IDs/barcodes.
    
    Returns:
        dict: Success status, system message, and a list of matching product records.
    """
    if not vendor_id:
        return {"success": False, "message": "Authentication Missing: Vendor ID is required.", "products": []}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database network pipeline offline.", "products": []}

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. Initialize the baseline query and tracking arguments array
        # The base constraint anchors every action behind the vendor data isolation wall
        sql_base = """
            SELECT product_id, product_name, category, purchase_price, 
                   selling_price, quantity, low_stock_limit, barcode 
            FROM products 
            WHERE vendor_id = %s
        """
        query_conditions = []
        execution_arguments = [vendor_id]

        # 2. Dynamically construct criteria evaluation blocks
        if product_id is not None:
            query_conditions.append("product_id = %s")
            execution_arguments.append(int(product_id))

        if barcode is not None:
            query_conditions.append("barcode = %s")
            execution_arguments.append(str(barcode).strip())

        if query_text:
            # SQL LIKE with percentage wildcards handles partial text matching
            query_conditions.append("product_name LIKE %s")
            execution_arguments.append(f"%{query_text.strip()}%")

        if category:
            query_conditions.append("category LIKE %s")
            execution_arguments.append(f"%{category.strip()}%")

        # 3. Assemble components if optional filters were declared
        if query_conditions:
            sql_base += " AND " + " AND ".join(query_conditions)

        # Apply sorting order to show newest additions first
        sql_base += " ORDER BY product_id DESC"

        # 4. Execute safe parameterized statement execution
        cursor.execute(sql_base, tuple(execution_arguments))
        matched_records = cursor.fetchall()

        if not matched_records:
            return {
                "success": True, 
                "message": "No products match the specified search parameters.", 
                "products": []
            }

        return {
            "success": True, 
            "message": f"Successfully isolated {len(matched_records)} matching catalog items.", 
            "products": matched_records
        }

    except Error as db_fault:
        return {"success": False, "message": f"Database search execution failure: {db_fault}", "products": []}
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def low_stock_alert(vendor_id):
    """
    Scans the inventory and isolates items where current stock matches or falls below
    the vendor-defined warning threshold (quantity <= low_stock_limit).
    
    Returns:
        dict: Success status, operational message, and the list of low stock items.
    """
    if not vendor_id:
        return {"success": False, "message": "Authentication Fault: Vendor ID is required.", "products": []}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "products": []}

    try:
        cursor = connection.cursor(dictionary=True)

        # Secure query isolating rows matching the formula condition within the vendor boundary
        query = """
            SELECT product_id, product_name, category, purchase_price, 
                   selling_price, quantity, low_stock_limit 
            FROM products 
            WHERE vendor_id = %s AND quantity <= low_stock_limit
            ORDER BY quantity ASC
        """
        
        cursor.execute(query, (vendor_id,))
        low_stock_items = cursor.fetchall()

        # Handle case where all inventory items have healthy, sufficient stock balances
        if not low_stock_items:
            return {
                "success": True, 
                "message": "Excellent! All inventory items have sufficient stock levels.", 
                "products": []
            }

        return {
            "success": True, 
            "message": f"Attention: {len(low_stock_items)} items are running low on stock. Please replenish soon.", 
            "products": low_stock_items
        }

    except Error as db_fault:
        return {"success": False, "message": f"Database scan execution failure: {db_fault}", "products": []}
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)