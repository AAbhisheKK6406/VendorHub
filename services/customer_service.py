import mysql.connector
from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def add_customer(vendor_id, name, phone, email=None, address=None):
    """
    Validates and registers a new customer under a specific vendor's account.
    Prevents duplicate phone numbers for the same vendor.
    """
    if not vendor_id or not name or not phone:
        return {"success": False, "message": "Missing required fields: Vendor ID, Name, and Phone are mandatory."}

    # Clean the name and phone strings safely
    name = name.strip()
    phone = phone.strip()
    email = email.strip().lower() if email and email.strip() else None
    address = address.strip() if address and address.strip() else None

    # Indian Phone Number Validation (Exactly 10 digits)
    if not phone.isdigit() or len(phone) != 10:
        return {"success": False, "message": "Validation Failure: Phone number must contain exactly 10 numeric digits."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # Confirm vendor validity
        vendor_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Unauthorized operation: Registered vendor not found."}

        # Prevent duplicate phone numbers under the same vendor
        duplicate_query = "SELECT customer_id FROM customers WHERE vendor_id = %s AND phone = %s"
        cursor.execute(duplicate_query, (vendor_id, phone))
        if cursor.fetchone():
            return {"success": False, "message": f"Conflict: A customer with phone number '{phone}' is already registered under your account."}

        # Insert record
        insert_query = """
            INSERT INTO customers (vendor_id, customer_name, phone, email, address)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (vendor_id, name, phone, email, address))
        connection.commit() 

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
    """
    if not vendor_id:
        return {"success": False, "message": "Authentication Missing: Vendor ID is required.", "customers": []}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "customers": []}

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT customer_id, customer_name, phone, email, address 
            FROM customers 
            WHERE vendor_id = %s 
            ORDER BY customer_name ASC
        """
        cursor.execute(query, (vendor_id,))
        customer_list = cursor.fetchall()

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
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def update_customer(vendor_id, customer_id, customer_name, phone, email=None, address=None):
    """
    Updates the profile of an existing customer belonging to the logged-in vendor.
    """
    if not vendor_id or not customer_id or not customer_name or not phone:
        return {"success": False, "message": "Validation Failure: Vendor ID, Customer ID, Name, and Phone are mandatory."}

    customer_name = customer_name.strip()
    phone = phone.strip()
    email = email.strip().lower() if email and email.strip() else None
    address = address.strip() if address and address.strip() else None

    if not phone.isdigit() or len(phone) != 10:
        return {"success": False, "message": "Validation Failure: Phone number must contain exactly 10 digits."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        # Confirm customer belongs to the active vendor session
        exist_query = "SELECT customer_id FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(exist_query, (customer_id, vendor_id))
        if not cursor.fetchone():
            return {"success": False, "message": "Operation Aborted: Customer profile not found or access denied."}

        # Check cross-profile duplication conflicts
        dup_query = "SELECT customer_id FROM customers WHERE vendor_id = %s AND phone = %s AND customer_id != %s"
        cursor.execute(dup_query, (vendor_id, phone, customer_id))
        if cursor.fetchone():
            return {"success": False, "message": f"Conflict: The phone number '{phone}' is already registered to another customer."}

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
    """
    if not vendor_id or not customer_id:
        return {"success": False, "message": "Validation Failure: Vendor ID and Customer ID are mandatory."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline."}

    try:
        cursor = connection.cursor(dictionary=True)

        check_query = "SELECT customer_name FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(check_query, (customer_id, vendor_id))
        customer_record = cursor.fetchone()

        if not customer_record:
            return {"success": False, "message": "Operation Aborted: Customer profile not found or access denied."}

        deleted_name = customer_record['customer_name']

        delete_query = "DELETE FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(delete_query, (customer_id, vendor_id))
        connection.commit()

        return {"success": True, "message": f"Customer '{deleted_name}' (ID: {customer_id}) has been successfully deleted."}

    except Error as db_err:
        return {"success": False, "message": f"Database execution failure during deletion: {db_err}"}
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def search_customers(vendor_id, search_name=None, phone=None, email=None, customer_id=None):
    """
    Dynamically filters and searches the vendor's customer directory.
    """
    if not vendor_id:
        return {"success": False, "message": "Authentication Missing: Vendor ID is required.", "customers": []}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database network pipeline offline.", "customers": []}

    try:
        cursor = connection.cursor(dictionary=True)
        sql_base = "SELECT customer_id, customer_name, phone, email, address FROM customers WHERE vendor_id = %s"
        query_conditions = []
        execution_arguments = [vendor_id]

        if customer_id is not None:
            query_conditions.append("customer_id = %s")
            execution_arguments.append(int(customer_id))

        if phone and phone.strip():
            query_conditions.append("phone = %s")
            execution_arguments.append(phone.strip())

        if email and email.strip():
            query_conditions.append("email = %s")
            execution_arguments.append(email.strip().lower())

        if search_name and search_name.strip():
            query_conditions.append("customer_name LIKE %s")
            execution_arguments.append(f"%{search_name.strip()}%")

        if query_conditions:
            sql_base += " AND " + " AND ".join(query_conditions)

        sql_base += " ORDER BY customer_name ASC"

        cursor.execute(sql_base, tuple(execution_arguments))
        matched_customers = cursor.fetchall()

        if not matched_customers:
            return {"success": True, "message": "No customer profiles match your search criteria.", "customers": []}

        return {"success": True, "message": f"Successfully found {len(matched_customers)} profiles.", "customers": matched_customers}

    except Error as db_fault:
        return {"success": False, "message": f"Database search execution failure: {db_fault}", "customers": []}
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)


def customer_purchase_history(vendor_id, customer_id):
    """
    Retrieves the complete transactional history and key summary metrics for a given customer.
    Fixes the total expense aggregation loop multiplier bug.
    """
    if not vendor_id or not customer_id:
        return {"success": False, "message": "Validation Failure: Vendor ID and Customer ID are required.", "history": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "history": None}

    try:
        cursor = connection.cursor(dictionary=True)

        check_query = "SELECT customer_name FROM customers WHERE customer_id = %s AND vendor_id = %s"
        cursor.execute(check_query, (customer_id, vendor_id))
        customer_record = cursor.fetchone()

        if not customer_record:
            return {"success": False, "message": "Access Denied: Customer profile not found or unauthorized.", "history": None}

        customer_name = customer_record['customer_name']

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
                    "bills": []
                }
            }

        bills_dict = {}
        total_spent = 0.00
        purchase_dates = []

        for row in raw_rows:
            sale_id = row['sale_id']
            
            if sale_id not in bills_dict:
                bills_dict[sale_id] = {
                    "bill_number": sale_id,
                    "bill_date": row['sale_date'],
                    "grand_total": float(row['grand_total']),
                    "items": []
                }
                # FIX: Increment spent total exactly once per distinctive bill entity
                total_spent += float(row['grand_total'])
                purchase_dates.append(row['sale_date'])

            bills_dict[sale_id]["items"].append({
                "product_id": row['product_id'],
                "product_name": row['product_name'],
                "quantity": row['quantity'],
                "selling_price": float(row['selling_price']),
                "subtotal": float(row['item_subtotal'])
            })

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

def get_customer_dashboard_metrics(vendor_id):
    """
    Exposes system-wide relationship metrics for customers tied to a vendor.
    """
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "data": None}

    try:
        cursor = connection.cursor(dictionary=True)

        # Counting unique customers who have entries in sales logs with this vendor
        query = """
            SELECT COUNT(DISTINCT customer_id) as total_customers 
            FROM sales 
            WHERE vendor_id = %s AND customer_id IS NOT NULL
        """
        cursor.execute(query, (vendor_id,))
        result = cursor.fetchone()

        return {
            "success": True,
            "message": "Customer dashboard metrics fetched successfully.",
            "data": {
                "total_customers": int(result["total_customers"]) if result else 0
            }
        }
    except Error as db_error:
        return {"success": False, "message": f"Database error in customer helper: {db_error}", "data": None}
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)