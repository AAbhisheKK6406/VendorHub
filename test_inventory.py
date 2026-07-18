""""import mysql.connector
from services.inventory_service import add_product
from database.db import get_database_connection, close_database_connection

def run_inventory_test():
    print("--- STARTING INVENTORY MODULE TEST ---")

    # Step A: Find a valid vendor from the database to link our product to
    connection = get_database_connection()
    if not connection:
        print("Test Aborted: Could not connect to the database to find a valid vendor ID.")
        return

    test_vendor_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM vendors LIMIT 1")
        vendor_record = cursor.fetchone()
        if vendor_record:
            test_vendor_id = vendor_record['id']
        else:
            print("Test Warning: No vendors found in your database. Please run test_auth.py first to create a vendor!")
            return
    except mysql.connector.Error as err:
        print(f"Error selecting vendor: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # Step B: Attempt to add a product using our service function
    print(f"\nAdding sample product for Vendor ID: {test_vendor_id}...")
    result = add_product(
        vendor_id=test_vendor_id,
        product_name="Pro Wireless Mouse",
        category="Electronics",
        purchase_price=15.50,
        selling_price=29.99,
        quantity=50,
        low_stock_limit=10,
        barcode="8801234567"
    )
    print(f"Service Output: {result}")

    # Step C: Verify the product exists in the table
    if result["success"]:
        print("\nVerifying database entry via: SELECT * FROM products...")
        verify_connection = get_database_connection()
        try:
            verify_cursor = verify_connection.cursor(dictionary=True)
            verify_cursor.execute("SELECT * FROM products ORDER BY product_id DESC LIMIT 1")
            inserted_record = verify_cursor.fetchone()
            
            print("\n--- DATABASE RECORD DETECTED ---")
            for key, val in inserted_record.items():
                print(f"{key}: {val}")
            print("--------------------------------")
            
        except mysql.connector.Error as err:
            print(f"Verification query failed: {err}")
        finally:
            verify_cursor.close()
            close_database_connection(verify_connection)

if __name__ == "__main__":
    run_inventory_test()


import mysql.connector
from services.inventory_service import view_products
from database.db import get_database_connection, close_database_connection

def run_view_products_test():
    print("--- STARTING INVENTORY MODULE: VIEW PRODUCTS TEST ---")

    # Step A: Find a valid vendor from your system to simulate a logged-in session
    connection = get_database_connection()
    if not connection:
        print("Test Aborted: Database connection offline.")
        return

    test_vendor_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, username FROM vendors LIMIT 1")
        vendor_record = cursor.fetchone()
        
        if vendor_record:
            test_vendor_id = vendor_record['id']
            print(f"Simulating logged-in session for Vendor: '{vendor_record['username']}' (ID: {test_vendor_id})")
        else:
            print("Test Setup Failed: No vendors exist. Please run test_auth.py first!")
            return
    except mysql.connector.Error as err:
        print(f"Failed to find test vendor: {err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # Step B: Call the view_products service function
    print("\nExecuting backend view_products()...")
    result = view_products(vendor_id=test_vendor_id)
    
    print(f"Service Execution Status: {result['success']}")
    print(f"Service Message: {result['message']}")

    # Step C: Format and display results in a readable layout
    if result["success"] and result["products"]:
        print("\n======================= LIVE INVENTORY CATALOG =======================")
        print(f"{'ID':<6} | {'PRODUCT NAME':<25} | {'CATEGORY':<15} | {'PRICE':<8} | {'STOCK':<6}")
        print("-" * 70)
        
        for prod in result["products"]:
            print(f"{prod['product_id']:<6} | {prod['product_name']:<25} | {prod['category']:<15} | ${prod['selling_price']:<7} | {prod['quantity']:<6}")
        print("======================================================================")
    else:
        print("\nNo inventory rows returned to display.")

if __name__ == "__main__":
    run_view_products_test()

import mysql.connector
from services.inventory_service import update_product
from database.db import get_database_connection, close_database_connection

def run_update_product_test():
    print("--- STARTING INVENTORY MODULE: UPDATE PRODUCT TEST (RUPEES FORMAT) ---")

    # Step A: Dynamically trace a target row inside products to update
    connection = get_database_connection()
    if not connection:
        print("Test Halting: Database offline.")
        return

    target_product_id = None
    target_vendor_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT product_id, vendor_id, product_name, selling_price FROM products LIMIT 1")
        existing_item = cursor.fetchone()

        if existing_item:
            target_product_id = existing_item['product_id']
            target_vendor_id = existing_item['vendor_id']
            print(f"Target Selected: '{existing_item['product_name']}' | Current Price: Rs. {existing_item['selling_price']}")
        else:
            print("Test Incomplete: No products exist in table. Add products before executing update tests.")
            return
    except mysql.connector.Error as db_err:
        print(f"Failed to find testing target parameters: {db_err}")
        return
    finally:
        cursor.close()
        close_database_connection(connection)

    # Step B: Call the service function to modify parameters using Rupee valuations
    print(f"\nModifying Product ID: {target_product_id} with new parameters...")
    test_result = update_product(
        vendor_id=target_vendor_id,
        product_id=target_product_id,
        product_name="Premium Ergonomic Mouse", # Updated name
        purchase_price=800.00,                 # Cost in Rupees
        selling_price=1499.00,                 # Selling Price in Rupees (₹)
        quantity=65                            # Adjusted inventory stock count
    )

    print(f"Execution Output: {test_result['message']}")

    # Step C: Use standard SELECT lookup to verify changes match expectations
    if test_result["success"]:
        print("\nVerifying data integrity state via: SELECT * FROM products...")
        verify_connection = get_database_connection()
        try:
            verify_cursor = verify_connection.cursor(dictionary=True)
            verify_cursor.execute("SELECT * FROM products WHERE product_id = %s", (target_product_id,))
            updated_row = verify_cursor.fetchone()

            print("\n======================= UPDATED RECORD PROFILE =======================")
            print(f"Product ID        : {updated_row['product_id']}")
            print(f"Vendor Account ID : {updated_row['vendor_id']}")
            print(f"Product Title     : {updated_row['product_name']}")
            print(f"Category Group    : {updated_row['category']}")
            print(f"Purchase Cost     : ₹ {updated_row['purchase_price']}")
            print(f"Retail Valuation  : ₹ {updated_row['selling_price']}") # Displayed clearly in Rupees
            print(f"Available Balance : {updated_row['quantity']} Units")
            print(f"Low Warning Limit : {updated_row['low_stock_limit']} Units")
            print("======================================================================")

        except mysql.connector.Error as db_err:
            print(f"Verification query failed: {db_err}")
        finally:
            verify_cursor.close()
            close_database_connection(verify_connection)

if __name__ == "__main__":
    run_update_product_test()"""
import mysql.connector
from services.inventory_service import low_stock_alert
from database.db import get_database_connection, close_database_connection

def display_alert_report(service_output):
    """Helper method to format the alert warning dashboard cleanly in Indian Rupees."""
    print(f"System Message: {service_output['message']}\n")
    
    if service_output["success"] and service_output["products"]:
        print("!" * 76)
        print(f" {'CRITICAL REORDER WARNING SYSTEM':^74} ")
        print("!" * 76)
        print(f"{'ID':<6} | {'PRODUCT NAME':<25} | {'PRICE':<12} | {'CURRENT STOCK':<13} | {'WARNING LIMIT':<12}")
        print("-" * 76)
        for prod in service_output["products"]:
            print(f"{prod['product_id']:<6} | {prod['product_name']:<25} | ₹ {prod['selling_price']:<10} | {prod['quantity']:<13} | {prod['low_stock_limit']:<12}")
        print("!" * 76)
    print("\n")

def run_low_stock_test_suite():
    print("======================================================================")
    print("      VENDORHUB INVENTORY MODULE: LOW STOCK ALERT EVALUATION          ")
    print("======================================================================\n")

    # Step A: Identify valid active session credentials from data layer
    connection = get_database_connection()
    if not connection:
        print("Test Setup Aborted: Database offline.")
        return

    test_vendor_id = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM vendors LIMIT 1")
        vendor = cursor.fetchone()
        if vendor:
            test_vendor_id = vendor['id']
        else:
            print("Setup Fault: No vendor accounts detected. Run test_auth.py first.")
            return
    finally:
        cursor.close()
        close_database_connection(connection)

    # TEST CASE 1: Standard Evaluation Scan
    print(f"[TEST 1] Triggering automated stock audit scan for Vendor ID: {test_vendor_id}...")
    scan_result = low_stock_alert(vendor_id=test_vendor_id)
    display_alert_report(scan_result)

    print("Verification complete. Cross-examine active table rows by executing:")
    print("SELECT product_id, product_name, quantity, low_stock_limit FROM products;\n")

if __name__ == "__main__":
    run_low_stock_test_suite()

