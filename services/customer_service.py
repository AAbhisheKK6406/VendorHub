import mysql.connector
from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def add_customer(vendor_id, name, phone, email=None, address=None):
    """
    Validates and registers a new customer under a specific vendor's account.
    Prevents duplicate phone numbers for the same vendor.
    
    Returns:
        dict: Success status and feedback message.
    """
    # 1. Basic validation of mandatory fields
    if not vendor_id or not name or not phone:
        return {"success": False, "message": "Missing required fields: Vendor ID, Name, and Phone are mandatory."}

    # Clean the name and phone strings
    name = name.strip()
    phone = phone.strip()
    email = email.strip() if email else None
    address = address.strip() if address else None

    # 2. Indian Phone Number Validation (Must be exactly 10 numeric digits)
    if not phone.isdigit() or len(phone) != 10:
        return {"success": False, "message": "Validation Failure: Phone number must contain exactly 10 numeric digits."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # 3. Check if vendor exists before continuing
        vendor_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Unauthorized operation: Registered vendor not found."}

        # 4. Prevent duplicate phone numbers under the same vendor
        duplicate_query = "SELECT customer_id FROM customers WHERE vendor_id = %s AND phone = %s"
        cursor.execute(duplicate_query, (vendor_id, phone))
        if cursor.fetchone():
            return {"success": False, "message": f"Conflict: A customer with phone number '{phone}' is already registered under your account."}

        # 5. Insert the new customer record
        insert_query = """
            INSERT INTO customers (vendor_id, customer_name, phone, email, address)
            VALUES (%s, %s, %s, %s, %s)
        """
        customer_data = (vendor_id, name, phone, email, address)
        cursor.execute(insert_query, customer_data)
        
        connection.commit()  # Save changes permanently to the disk

        return {"success": True, "message": f"Customer '{name}' successfully registered!"}

    except Error as db_err:
        return {"success": False, "message": f"Database processing failure: {db_err}"}

    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def view_customers(vendor_id):
    """
    Retrieves all customer records belonging to a specific vendor, sorted alphabetically.
    
    Args:
        vendor_id (int): The unique ID of the logged-in vendor.
        
    Returns:
        dict: A status dictionary containing 'success', 'message', and a 'customers' list.
    """
    # 1. Validate baseline parameter presence
    if not vendor_id:
        return {"success": False, "message": "Authentication Missing: Vendor ID is required.", "customers": []}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "customers": []}

    try:
        # Open a dictionary cursor to automatically map database records to key-value pairs
        cursor = connection.cursor(dictionary=True)

        # 2. Parameterized query isolating rows behind the vendor boundary, ordered alphabetically
        # Using 'customer_name' to match your exact database column schema spelling
        query = """
            SELECT customer_id, customer_name, phone, email, address 
            FROM customers 
            WHERE vendor_id = %s 
            ORDER BY customer_name ASC
        """
        
        cursor.execute(query, (vendor_id,))
        customer_list = cursor.fetchall()

        # 3. Intercept empty state conditions gracefully
        if not customer_list:
            return {
                "success": True, 
                "message": "Your customer directory is currently empty. Start by adding your first customer!", 
                "customers": []
            }

        return {
            "success": True, 
            "message": f"Successfully retrieved {len(customer_list)} customer records.", 
            "customers": customer_list
        }

    except Error as db_err:
        return {"success": False, "message": f"Database read transaction failed: {db_err}", "customers": []}

    finally:
        # Release database server channel resources
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def update_customer(vendor_id, customer_id, customer_name, phone, email=None, address=None):
    """
    Updates the profile of an existing customer belonging to the logged-in vendor.
    Validates input parameters and ensures no duplicate phone numbers exist.
    
    Returns:
        dict: Success status and feedback message.
    """
    # 1. Validation of required inputs
    if not vendor_id or not customer_id or not customer_name or not phone:
        return {"success": False, "message": "Validation Failure: Vendor ID, Customer ID, Name, and Phone are mandatory."}

    # Clean the string parameters
    customer_name = customer_name.strip()
    phone = phone.strip()
    email = email.strip() if email else None
    address = address.strip() if address else None

    # 2. Check phone formatting (10 digits)
    if not phone.isdigit() or len(phone) != 10:
        return {"success": False, "message": "Validation Failure: Phone number must contain exactly 10 digits."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # 3. Check if the customer exists and actually belongs to this vendor
        exist_query = "SELECT customer_id FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(exist_query, (customer_id, vendor_id))
        if not cursor.fetchone():
            return {"success": False, "message": "Operation Aborted: Customer profile not found or access denied."}

        # 4. Check if the new phone number is already assigned to a DIFFERENT customer under this vendor
        dup_query = "SELECT customer_id FROM customers WHERE vendor_id = %s AND phone = %s AND customer_id != %s"
        cursor.execute(dup_query, (vendor_id, phone, customer_id))
        if cursor.fetchone():
            return {"success": False, "message": f"Conflict: The phone number '{phone}' is already registered to another customer."}

        # 5. Execute the update
        update_query = """
            UPDATE customers 
            SET customer_name = %s, phone = %s, email = %s, address = %s 
            WHERE customer_id = %s AND vendor_id = %s
        """
        cursor.execute(update_query, (customer_name, phone, email, address, customer_id, vendor_id))
        connection.commit()

        return {"success": True, "message": f"Customer profile for '{customer_name}' successfully updated!"}

    except Error as db_err:
        return {"success": False, "message": f"Database update failure: {db_err}"}

    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def delete_customer(vendor_id, customer_id):
    """
    Safely deletes a customer record belonging to the logged-in vendor.
    Checks if the customer exists before attempting to delete.
    
    Args:
        vendor_id (int): The ID of the logged-in vendor.
        customer_id (int): The ID of the customer to be deleted.
        
    Returns:
        dict: Success status and feedback message.
    """
    # 1. Validate baseline parameters
    if not vendor_id or not customer_id:
        return {"success": False, "message": "Validation Failure: Vendor ID and Customer ID are mandatory."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Check if the customer exists and actually belongs to this vendor
        check_query = "SELECT customer_id, customer_name FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(check_query, (customer_id, vendor_id))
        customer_record = cursor.fetchone()

        if not customer_record:
            return {
                "success": False, 
                "message": "Operation Aborted: Customer profile not found or access denied."
            }

        # Keep the customer name for a friendly success message
        deleted_name = customer_record['customer_name']

        # 3. Execute the deletion
        delete_query = "DELETE FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(delete_query, (customer_id, vendor_id))
        
        # 4. Commit changes to write deletion permanently to the disk
        connection.commit()

        return {
            "success": True, 
            "message": f"Customer '{deleted_name}' (ID: {customer_id}) has been successfully deleted from your directory."
        }

    except Error as db_err:
        return {"success": False, "message": f"Database execution failure during deletion: {db_err}"}

    finally:
        # 5. Resource cleanup
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)
def search_customers(vendor_id, search_name=None, phone=None, email=None, customer_id=None):
    """
    Dynamically filters and searches the vendor's customer directory.
    Supports partial matching for names and exact matching for phone numbers, emails, and IDs.
    
    Returns:
        dict: Success status, descriptive message, and a list of matching customer records.
    """
    # 1. Enforce active session baseline constraint
    if not vendor_id:
        return {"success": False, "message": "Authentication Missing: Vendor ID is required.", "customers": []}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database network pipeline offline.", "customers": []}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Setup baseline SQL query locked behind the active vendor wall
        sql_base = """
            SELECT customer_id, customer_name, phone, email, address 
            FROM customers 
            WHERE vendor_id = %s
        """
        query_conditions = []
        execution_arguments = [vendor_id]

        # 3. Append dynamic filtering clauses based on provided search inputs
        if customer_id is not None:
            query_conditions.append("customer_id = %s")
            execution_arguments.append(int(customer_id))

        if phone:
            query_conditions.append("phone = %s")
            execution_arguments.append(phone.strip())

        if email:
            query_conditions.append("email = %s")
            execution_arguments.append(email.strip().lower())

        if search_name:
            # SQL LIKE with wildcards allows partial name match
            query_conditions.append("customer_name LIKE %s")
            execution_arguments.append(f"%{search_name.strip()}%")

        # 4. Join additional query parameters using AND gates if active search filters exist
        if query_conditions:
            sql_base += " AND " + " AND ".join(query_conditions)

        # Apply standard alphabetical sorting to results
        sql_base += " ORDER BY customer_name ASC"

        # 5. Execute secure parameterized query
        cursor.execute(sql_base, tuple(execution_arguments))
        matched_customers = cursor.fetchall()

        # 6. Intercept empty result states gracefully
        if not matched_customers:
            return {
                "success": True, 
                "message": "No customer profiles match your search criteria.", 
                "customers": []
            }

        return {
            "success": True, 
            "message": f"Successfully found {len(matched_customers)} matching customer profiles.", 
            "customers": matched_customers
        }

    except Error as db_fault:
        return {"success": False, "message": f"Database search execution failure: {db_fault}", "customers": []}
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def customer_purchase_history(vendor_id, customer_id):
    """
    Retrieves the complete transactional history and key summary metrics for a given customer.
    Ensures that data boundaries match the current logged-in vendor context securely.
    
    Returns:
        dict: Operational success status, response message, history summaries, and bill items.
    """
    if not vendor_id or not customer_id:
        return {"success": False, "message": "Validation Failure: Vendor ID and Customer ID are required.", "history": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "history": None}

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. Authority Validation: Confirm customer ownership boundary matching
        check_query = "SELECT customer_name FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(check_query, (customer_id, vendor_id))
        customer_record = cursor.fetchone()

        if not customer_record:
            return {"success": False, "message": "Access Denied: Customer profile not found or unauthorized.", "history": None}

        customer_name = customer_record['customer_name']

        # 2. Main Relational Query utilizing SQL JOINs to pull down transaction details
        query = """
            SELECT 
                s.sale_id,
                s.sale_date,
                s.grand_total,
                si.product_id,
                p.product_name,
                si.quantity,
                si.selling_price,
                (si.quantity * si.selling_price) AS item_subtotal
            FROM sales s
            INNER JOIN sale_items si ON s.sale_id = si.sale_id
            INNER JOIN products p ON si.product_id = p.product_id
            WHERE s.customer_id = %s AND s.vendor_id = %s
            ORDER BY s.sale_date DESC, s.sale_id DESC
        """
        cursor.execute(query, (customer_id, vendor_id))
        raw_rows = cursor.fetchall()

        # 3. Handle empty transaction histories gracefully
        if not raw_rows:
            return {
                "success": True,
                "message": f"Customer '{customer_name}' has not made any purchases yet.",
                "history": {
                    "customer_name": customer_name,
                    "total_orders": 0,
                    "total_spent": 0.00,
                    "first_purchase_date": None,
                    "last_purchase_date": None,
                    "bills": {}
                }
            }

        # 4. Process flat data into nested bill structures and compile metrics
        bills_dict = {}
        total_spent = 0.00
        purchase_dates = []

        for row in raw_rows:
            sale_id = row['sale_id']
            
            # If the bill bucket hasn't been initialized yet, build it out
            if sale_id not in bills_dict:
                bills_dict[sale_id] = {
                    "bill_number": sale_id,
                    "bill_date": row['sale_date'],
                    "grand_total": float(row['grand_total']),
                    "items": []
                }
                # Track metadata summaries
                total_spent += float(row['grand_total'])
                purchase_dates.append(row['sale_date'])

            # Add the individual line item to the bill
            bills_dict[sale_id]["items"].append({
                "product_id": row['product_id'],
                "product_name": row['product_name'],
                "quantity": row['quantity'],
                "selling_price": float(row['selling_price']),
                "subtotal": float(row['item_subtotal'])
            })

        # Compile summaries
        summary_metrics = {
            "customer_name": customer_name,
            "total_orders": len(bills_dict),
            "total_spent": round(total_spent, 2),
            "first_purchase_date": min(purchase_dates) if purchase_dates else None,
            "last_purchase_date": max(purchase_dates) if purchase_dates else None,
            "bills": list(bills_dict.values())
        }

        return {
            "success": True,
            "message": f"Successfully compiled purchase history for customer '{customer_name}'.",
            "history": summary_metrics
        }

    except Error as db_err:
        return {"success": False, "message": f"Database processing failure: {db_err}", "history": None}

    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)