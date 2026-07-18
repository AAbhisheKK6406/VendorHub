import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_database_connection, close_database_connection

def hash_password(password):
    """
    Converts a plain-text password into a secure, one-way cryptographic hash.
    """
    return generate_password_hash(password)

def verify_password(password, password_hash):
    """
    Compares a plain-text password against a stored hash.
    Returns True if they match, False otherwise.
    """
    return check_password_hash(password_hash, password)

def register_vendor(username, email, password, business_name, phone=None):
    """
    Validates and signs up a new vendor into the system.
    Returns a dictionary with status and message.
    """
    # 1. Simple Input Validation
    if not username or not email or not password or not business_name:
        return {"success": False, "message": "Missing required fields."}

    # 2. Secure the password
    secure_hash = hash_password(password)

    # 3. Connect and write to the database
    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database connection failed."}

    try:
        cursor = connection.cursor(dictionary=True)

        # Check if username or email already exists
        check_query = "SELECT id FROM vendors WHERE username = %s OR email = %s"
        cursor.execute(check_query, (username, email))
        existing_vendor = cursor.fetchone()

        if existing_vendor:
            return {"success": False, "message": "Username or Email is already registered."}

        # Insert new vendor data
        insert_query = """
            INSERT INTO vendors (username, email, password_hash, business_name, phone)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (username, email, secure_hash, business_name, phone))
        connection.commit() # Save changes permanently
        
        return {"success": True, "message": "Vendor registered successfully!"}

    except Error as db_error:
        return {"success": False, "message": f"Database error during registration: {db_error}"}
        
    finally:
        # Clean up database resources
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)

def login_vendor(username_or_email, password):
    """
    Verifies a vendor's credentials.
    Returns a dictionary containing authentication status and vendor data if successful.
    """
    if not username_or_email or not password:
        return {"success": False, "message": "Username/Email and password are required."}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database connection failed."}

    try:
        cursor = connection.cursor(dictionary=True)

        # Look up vendor by username or email
        login_query = "SELECT * FROM vendors WHERE username = %s OR email = %s"
        cursor.execute(login_query, (username_or_email, username_or_email))
        vendor = cursor.fetchone()

        # If vendor doesn't exist
        if not vendor:
            return {"success": False, "message": "Invalid username or email."}

        # Check if the vendor account has been deactivated
        if not vendor['is_active']:
            return {"success": False, "message": "This account is currently suspended."}

        # Verify password match
        if verify_password(password, vendor['password_hash']):
            # Strip the password hash before sending the vendor profile data up to the application layer
            del vendor['password_hash']
            return {"success": True, "message": "Login successful!", "vendor": vendor}
        else:
            return {"success": False, "message": "Invalid password."}

    except Error as db_error:
        return {"success": False, "message": f"Database error during login: {db_error}"}
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_database_connection(connection)