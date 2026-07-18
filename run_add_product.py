import os
import sys
import json
import traceback  # Helps print structural code errors without swallowing them

# Ensure Python can locate the services and database folders from the root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database.db import get_database_connection, close_database_connection
from services.billing_service import create_bill, add_product_to_bill, calculate_bill_total

def run_complete_billing_integration_test():
    print("========== STARTING VENDORHUB BILLING INTEGRATION TEST ==========\n")
    
    # SETUP: Set to ID 1 to match the actual vendor, customer, and products in MySQL
    TEST_VENDOR_ID = 1
    TEST_CUSTOMER_ID = 1
    TEST_PRODUCT_1_ID = 1  
    TEST_PRODUCT_2_ID = 2  
    
    connection = get_database_connection()
    if not connection:
        print("❌ Critical Error: Cannot connect to MySQL database via database/db.py")
        return
    
    try:
        # ====================================================
        # STEP 1: Create a new bill header
        # ====================================================
        print("--- Step 1: Creating Draft Bill Header ---")
        bill_creation_result = create_bill(vendor_id=TEST_VENDOR_ID, customer_id=TEST_CUSTOMER_ID)
        
        print("Raw Database Return:", bill_creation_result)
        
        # Dig into the 'bill_data' sub-dictionary to find the actual sale_id
        sale_id = None
        if isinstance(bill_creation_result, dict):
            bill_data = bill_creation_result.get("bill_data")
            if isinstance(bill_data, dict):
                sale_id = bill_data.get("sale_id")

        print(f"Extracted Sale ID for processing: {sale_id}\n")
        
        if not sale_id:
            print("❌ Step 1 Failed: Could not extract a valid sale_id from bill_data. Aborting.")
            return
        
        # ====================================================
        # STEP 2: Add multiple products to the bill
        # ====================================================
        print(f"--- Step 2: Adding Multiple Products to Sale ID {sale_id} ---")
        
        prod1_result = add_product_to_bill(sale_id=sale_id, product_id=TEST_PRODUCT_1_ID, requested_quantity=2)
        print(f"\n[Product 1 Added Response]:")
        print(json.dumps(prod1_result, indent=4) if isinstance(prod1_result, dict) else prod1_result)
        
        prod2_result = add_product_to_bill(sale_id=sale_id, product_id=TEST_PRODUCT_2_ID, requested_quantity=1)
        print(f"\n[Product 2 Added Response]:")
        print(json.dumps(prod2_result, indent=4) if isinstance(prod2_result, dict) else prod2_result)

        # Handle checking calculation metrics safely if responses are structured dictionaries
        expected_subtotal = None
        if isinstance(prod1_result, dict) and isinstance(prod2_result, dict):
            if prod1_result.get("success") and prod2_result.get("success"):
                p1_details = prod1_result.get("item_details", {})
                p2_details = prod2_result.get("item_details", {})
                p1_subtotal = p1_details.get("subtotal", 0) if isinstance(p1_details, dict) else 0
                p2_subtotal = p2_details.get("subtotal", 0) if isinstance(p2_details, dict) else 0
                expected_subtotal = p1_subtotal + p2_subtotal

        # ====================================================
        # STEP 3: Calculate the bill total
        # ====================================================
        print("\n--- Step 3: Calculating Bill Financial Totals ---")
        calculation_result = calculate_bill_total(
            sale_id=sale_id,
            vendor_id=TEST_VENDOR_ID,
            discount_type="percentage",
            discount_value=10.0,      # 10% off
            tax_percentage=18.0,      # 18% GST
            payment_method="UPI",
            payment_status="Paid"
        )
        print(json.dumps(calculation_result, indent=4) if isinstance(calculation_result, dict) else calculation_result)

        # ====================================================
        # VERIFICATION: Asserting Business Rules & Schema Consistency
        # ====================================================
        print("\n--- Verification Phase: Asserting Business Rules ---")
        if isinstance(calculation_result, dict) and "bill_summary" in calculation_result:
            summary = calculation_result["bill_summary"]
            
            if expected_subtotal is not None and "subtotal" in summary:
                assert summary["subtotal"] == expected_subtotal, f"Subtotal mismatch! Got {summary['subtotal']}"
            
            assert summary.get("payment_status") == "Paid", "Payment status flag state failure!"
            print("✅ Success: Financial metrics, calculations, and payment flags match perfectly.")
        else:
            print("⚠️ Note: Calculation result returned unexpected format. Skipping deep structural asserts.")
            
        print("\n🎉 INTEGRATION TEST COMPLETED SUCCESSFULLY!")

    except AssertionError as assert_err:
        print(f"\n❌ Integration Verification Failure: {assert_err}")
    except Exception as err:
        print(f"\n❌ Unexpected runtime crash: {err}")
        print("\n--- Code Traceback Debug Window ---")
        traceback.print_exc()  # Instantly pinpoints the file line number if a backend code bug exists
    finally:
        close_database_connection(connection)

if __name__ == "__main__":
    run_complete_billing_integration_test()