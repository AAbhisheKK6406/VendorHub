import mysql.connector
from services.customer_service import add_customer
from database.db import get_database_connection, close_database_connection

def run_customer_test():
    print("======================================================================")
    print("             VENDORHUB CUSTOMER MODULE: ADD CUSTOMER TEST             ")
    print("======================================================================\n")

    connection = get_database_connection()
    if not connection:
        print("Test Aborted: Database connection offline.")
        return

    test_vendor_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        # FIX: Select 'id' (not vendor_id) from the vendors table
        cursor.execute("SELECT id, username FROM vendors LIMIT 1")
        vendor_record = cursor.fetchone()
        
        if vendor_record:
            test_vendor_id = vendor_record['id']
            print(f"Active Session Context: Testing for Vendor '{vendor_record['username']}' (ID: {test_vendor_id})")
        else:
            print("Setup Fault: No registered vendors found. Run test_auth.py first!")
            return
    except mysql.connector.Error as err:
        print(f"Error fetching test vendor: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # ----------------------------------------------------------------------
    # TEST CASE 1: Add a brand new valid customer
    # ----------------------------------------------------------------------
    print("\n[TEST CASE 1] Adding a new customer profile...")
    result_1 = add_customer(
        vendor_id=test_vendor_id,
        name="Arjun Sharma",
        phone="9876543210",
        email="arjun.sharma@email.com",
        address="Sector 15, Vasundhara, Ghaziabad"
    )
    print(f"Response Status: {result_1['success']}")
    print(f"Response Message: {result_1['message']}")

    # ----------------------------------------------------------------------
    # TEST CASE 2: Attempt duplicate entry using the exact same phone number
    # ----------------------------------------------------------------------
    print("\n[TEST CASE 2] Attempting to add the duplicate customer again...")
    result_2 = add_customer(
        vendor_id=test_vendor_id,
        name="Arjun Kumar",
        phone="9876543210",
        email="arjun.kumar@email.com"
    )
    print(f"Response Status: {result_2['success']}")
    print(f"Response Message: {result_2['message']}")

    # ----------------------------------------------------------------------
    # STEP B: Verify results directly from the Database
    # ----------------------------------------------------------------------
    print("\nVerifying database records via: SELECT * FROM customers...")
    verify_connection = get_database_connection()
    try:
        verify_cursor = verify_connection.cursor(dictionary=True)
        verify_cursor.execute("SELECT customer_id, vendor_id, customer_name, phone, email, address FROM customers WHERE vendor_id = %s", (test_vendor_id,))
        records = verify_cursor.fetchall()

        print("\n========================= LIVE DATABASE RECORDS =========================")
        print(f"{'CUST_ID':<8} | {'VENDOR ID':<9} | {'NAME':<15} | {'PHONE':<11} | {'EMAIL':<22}")
        print("-" * 75)
        for customer in records:
            print(f"{customer['customer_id']:<8} | {customer['vendor_id']:<9} | {customer['customer_name']:<15} | {customer['phone']:<11} | {str(customer['email']):<22}")
        print("=========================================================================")

    except mysql.connector.Error as err:
        print(f"Verification query failed: {err}")
    finally:
        verify_cursor.close()
        close_database_connection(verify_connection)

if __name__ == "__main__":
    run_customer_test()

import mysql.connector
from services.customer_service import view_customers
from database.db import get_database_connection, close_database_connection

"""def run_view_customers_test():
    print("======================================================================")
    print("           VENDORHUB CUSTOMER MODULE: VIEW CUSTOMERS TEST             ")
    print("======================================================================\n")

    # Step A: Identify an active vendor context row in the master table
    connection = get_database_connection()
    if not connection:
        print("Test Aborted: Database connection offline.")
        return

    test_vendor_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        # Using 'id' for vendors table to match your schema setup
        cursor.execute("SELECT id, username FROM vendors LIMIT 1")
        vendor_record = cursor.fetchone()
        
        if vendor_record:
            test_vendor_id = vendor_record['id']
            print(f"Simulating Active Session Context for Vendor: '{vendor_record['username']}' (ID: {test_vendor_id})")
        else:
            print("Setup Fault: No registered vendors found. Run your authentication test scripts first!")
            return
    except mysql.connector.Error as err:
        print(f"Error accessing database setup variables: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # Step B: Call the core service feature function
    print("\nExecuting view_customers() service engine component...")
    result = view_customers(vendor_id=test_vendor_id)
    
    print(f"Service Call Success Flag: {result['success']}")
    print(f"Service Return Message    : {result['message']}")

    # Step C: Format output nicely to review chronological alphabetical order
    if result["success"] and result["customers"]:
        print("\n========================= ALPHABETICAL CUSTOMER DIRECTORY =========================")
        print(f"{'CUST_ID':<8} | {'CUSTOMER FULL NAME':<22} | {'CONTACT PHONE':<13} | {'EMAIL ADDRESS':<25}")
        print("-" * 76)
        
        for cust in result["customers"]:
            email_display = cust['email'] if cust['email'] else "N/A"
            print(f"{cust['customer_id']:<8} | {cust['customer_name']:<22} | {cust['phone']:<13} | {email_display:<25}")
        print("===================================================================================\n")
    else:
        print("\nNotice: No customer list returned to display layout.\n")

    print("Verification complete. Confirm live index metrics manually by running:")
    print("SELECT * FROM customers;\n")

if __name__ == "__main__":
    run_view_customers_test()


import mysql.connector
from services.customer_service import update_customer
from database.db import get_database_connection, close_database_connection

def run_update_test():
    print("======================================================================")
    print("           VENDORHUB CUSTOMER MODULE: UPDATE CUSTOMER TEST            ")
    print("======================================================================\n")

    connection = get_database_connection()
    if not connection:
        print("Test Aborted: Database connection offline.")
        return

    test_vendor_id = None
    target_customer_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        # 1. Grab a valid vendor
        cursor.execute("SELECT id FROM vendors LIMIT 1")
        vendor = cursor.fetchone()
        if vendor:
            test_vendor_id = vendor['id']
            
            # 2. Grab a customer registered under this vendor
            cursor.execute("SELECT customer_id FROM customers WHERE vendor_id = %s LIMIT 1", (test_vendor_id,))
            customer = cursor.fetchone()
            if customer:
                target_customer_id = customer['customer_id']
            else:
                print("Setup Failure: No test customers found. Run test_add_customer.py first!")
                return
        else:
            print("Setup Failure: No registered vendors found. Run test_auth.py first!")
            return
    except mysql.connector.Error as err:
        print(f"Database setup lookup failed: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # ----------------------------------------------------------------------
    # TEST CASE 1: Successful Update on an Existing Customer
    # ----------------------------------------------------------------------
    print(f"[TEST CASE 1] Updating Customer ID {target_customer_id} (Changing name & address)...")
    res_1 = update_customer(
        vendor_id=test_vendor_id,
        customer_id=target_customer_id,
        customer_name="Arjun S. Sharma",  # Appending middle initial
        phone="9876543210",               # Unchanged phone
        email="arjun.sharma@newemail.com", # Updated Email
        address="Flat 402, Sector 15, Vasundhara, Ghaziabad" # Updated Address
    )
    print(f"Response Status : {res_1['success']}")
    print(f"Response Message: {res_1['message']}")

    # ----------------------------------------------------------------------
    # TEST CASE 2: Update Attempt on a Non-Existent Customer
    # ----------------------------------------------------------------------
    print("\n[TEST CASE 2] Attempting to update an invalid Customer ID (99999)...")
    res_2 = update_customer(
        vendor_id=test_vendor_id,
        customer_id=99999,
        customer_name="John Doe",
        phone="9999999999"
    )
    print(f"Response Status : {res_2['success']}")
    print(f"Response Message: {res_2['message']}")

    # ----------------------------------------------------------------------
    # STEP B: Database Verification Lookup
    # ----------------------------------------------------------------------
    print("\nVerifying updated database records via: SELECT * FROM customers...")
    verify_conn = get_database_connection()
    try:
        verify_cursor = verify_conn.cursor(dictionary=True)
        verify_cursor.execute("SELECT customer_id, vendor_id, customer_name, phone, email, address FROM customers WHERE vendor_id = %s", (test_vendor_id,))
        records = verify_cursor.fetchall()

        print("\n========================= LIVE DATABASE RECORDS =========================")
        print(f"{'CUST_ID':<8} | {'VENDOR ID':<9} | {'NAME':<18} | {'PHONE':<11} | {'EMAIL':<22}")
        print("-" * 75)
        for customer in records:
            print(f"{customer['customer_id']:<8} | {customer['vendor_id']:<9} | {customer['customer_name']:<18} | {customer['phone']:<11} | {str(customer['email']):<22}")
        print("=========================================================================")

    except mysql.connector.Error as err:
        print(f"Verification query failed: {err}")
    finally:
        verify_cursor.close()
        close_database_connection(verify_conn)

if __name__ == "__main__":
    run_update_test()
import mysql.connector
from services.customer_service import delete_customer
from database.db import get_database_connection, close_database_connection

def run_delete_test():
    print("======================================================================")
    print("           VENDORHUB CUSTOMER MODULE: DELETE CUSTOMER TEST            ")
    print("======================================================================\n")

    connection = get_database_connection()
    if not connection:
        print("Test Aborted: Database connection offline.")
        return

    test_vendor_id = None
    target_customer_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        # 1. Fetch a valid active vendor
        cursor.execute("SELECT id FROM vendors LIMIT 1")
        vendor = cursor.fetchone()
        if vendor:
            test_vendor_id = vendor['id']
            
            # 2. Fetch an existing customer owned by this vendor to delete
            cursor.execute("SELECT customer_id FROM customers WHERE vendor_id = %s LIMIT 1", (test_vendor_id,))
            customer = cursor.fetchone()
            if customer:
                target_customer_id = customer['customer_id']
            else:
                print("Setup Failure: No test customers found in table. Run test_add_customer.py first!")
                return
        else:
            print("Setup Failure: No registered vendors found in system. Run test_auth.py first!")
            return
    except mysql.connector.Error as err:
        print(f"Database lookup setup failed: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # ----------------------------------------------------------------------
    # TEST CASE 1: Successfully delete an existing customer
    # ----------------------------------------------------------------------
    print(f"[TEST CASE 1] Deleting Customer ID {target_customer_id} belonging to Vendor {test_vendor_id}...")
    res_1 = delete_customer(vendor_id=test_vendor_id, customer_id=target_customer_id)
    print(f"Response Status : {res_1['success']}")
    print(f"Response Message: {res_1['message']}")

    # ----------------------------------------------------------------------
    # TEST CASE 2: Try deleting a non-existent customer
    # ----------------------------------------------------------------------
    print("\n[TEST CASE 2] Attempting to delete a non-existent Customer ID (99999)...")
    res_2 = delete_customer(vendor_id=test_vendor_id, customer_id=99999)
    print(f"Response Status : {res_2['success']}")
    print(f"Response Message: {res_2['message']}")

    # ----------------------------------------------------------------------
    # STEP B: Database Verification Lookup
    # ----------------------------------------------------------------------
    print("\nVerifying database records after deletion via: SELECT * FROM customers...")
    verify_conn = get_database_connection()
    try:
        verify_cursor = verify_conn.cursor(dictionary=True)
        verify_cursor.execute("SELECT customer_id, vendor_id, customer_name, phone, email, address FROM customers WHERE vendor_id = %s", (test_vendor_id,))
        records = verify_cursor.fetchall()

        print("\n========================= LIVE DATABASE RECORDS =========================")
        if not records:
            print("                Table Status: No customer records exist.                ")
        else:
            print(f"{'CUST_ID':<8} | {'VENDOR ID':<9} | {'NAME':<18} | {'PHONE':<11} | {'EMAIL':<22}")
            print("-" * 75)
            for customer in records:
                print(f"{customer['customer_id']:<8} | {customer['vendor_id']:<9} | {customer['customer_name']:<18} | {customer['phone']:<11} | {str(customer['email']):<22}")
        print("=========================================================================")

    except mysql.connector.Error as err:
        print(f"Verification query failed: {err}")
    finally:
        verify_cursor.close()
        close_database_connection(verify_conn)

if __name__ == "__main__":
    run_delete_test()

import mysql.connector
from services.customer_service import search_customers
from database.db import get_database_connection, close_database_connection

def display_search_results(service_output):
    
    print(f"Service Message: {service_output['message']}")
    if service_output["success"] and service_output["customers"]:
        print("-" * 80)
        print(f"{'CUST_ID':<8} | {'CUSTOMER FULL NAME':<22} | {'PHONE':<12} | {'EMAIL ADDRESS':<25}")
        print("-" * 80)
        for cust in service_output["customers"]:
            email_display = cust['email'] if cust['email'] else "N/A"
            print(f"{cust['customer_id']:<8} | {cust['customer_name']:<22} | {cust['phone']:<12} | {email_display:<25}")
        print("-" * 80)
    print("\n")

def run_search_test_suite():
    print("======================================================================")
    print("           VENDORHUB CUSTOMER MODULE: SEARCH CUSTOMERS TEST           ")
    print("======================================================================\n")

    # Step A: Locate active test parameters from database schema
    connection = get_database_connection()
    if not connection:
        print("Test Setup Aborted: Database connection offline.")
        return

    test_vendor_id = None
    sample_cust_id = None
    sample_phone = None
    sample_email = None

    try:
        cursor = connection.cursor(dictionary=True)
        # Fetch active test credentials
        cursor.execute("SELECT id FROM vendors LIMIT 1")
        vendor = cursor.fetchone()
        if vendor:
            test_vendor_id = vendor['id']
            
            # Fetch a customer linked to this vendor for targeting search tests
            cursor.execute("SELECT customer_id, phone, email FROM customers WHERE vendor_id = %s LIMIT 1", (test_vendor_id,))
            customer = cursor.fetchone()
            if customer:
                sample_cust_id = customer['customer_id']
                sample_phone = customer['phone']
                sample_email = customer['email']
            else:
                print("Setup Failure: No test customers found. Run test_add_customer.py first!")
                return
        else:
            print("Setup Failure: No registered vendors found. Run test_auth.py first!")
            return
    except mysql.connector.Error as err:
        print(f"Setup Lookup Error: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # ----------------------------------------------------------------------
    # TEST CASE 1: Partial Search by Customer Name
    # ----------------------------------------------------------------------
    print("[TEST CASE 1] Searching by partial name: 'Sharma'...")
    res_name = search_customers(vendor_id=test_vendor_id, search_name="Sharma")
    display_search_results(res_name)

    # ----------------------------------------------------------------------
    # TEST CASE 2: Exact Search by Phone Number
    # ----------------------------------------------------------------------
    print(f"[TEST CASE 2] Searching by exact phone number: '{sample_phone}'...")
    res_phone = search_customers(vendor_id=test_vendor_id, phone=sample_phone)
    display_search_results(res_phone)

    # ----------------------------------------------------------------------
    # TEST CASE 3: Exact Search by Email Address
    # ----------------------------------------------------------------------
    if sample_email:
        print(f"[TEST CASE 3] Searching by exact email address: '{sample_email}'...")
        res_email = search_customers(vendor_id=test_vendor_id, email=sample_email)
        display_search_results(res_email)
    else:
        print("[TEST CASE 3] Skipped (No email configured for target test profile).\n")

    # ----------------------------------------------------------------------
    # TEST CASE 4: Exact Search by Customer ID
    # ----------------------------------------------------------------------
    print(f"[TEST CASE 4] Searching by unique customer ID: {sample_cust_id}...")
    res_id = search_customers(vendor_id=test_vendor_id, customer_id=sample_cust_id)
    display_search_results(res_id)

    # ----------------------------------------------------------------------
    # TEST CASE 5: Search for Non-Existent Customer
    # ----------------------------------------------------------------------
    print("[TEST CASE 5] Searching for invalid customer criteria...")
    res_none = search_customers(vendor_id=test_vendor_id, search_name="NonExistentName")
    display_search_results(res_none)

    print("Search test cases complete. Cross-check your total database records using:")
    print("SELECT * FROM customers;\n")

if __name__ == "__main__":
    run_search_test_suite()"""