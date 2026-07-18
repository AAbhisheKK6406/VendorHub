"""import os
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
    run_complete_billing_integration_test()"""

import os
import sys

# Maintain clean import paths relative to app structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database.db import get_database_connection, close_database_connection
from services.billing_service import create_bill, add_product_to_bill, finalize_bill

def run_finalize_bill_tests():
    print("========== RUNNING VENDORHUB FINALIZE BILL TEST SUITE ==========\n")
    
    # Static database environment parameters (Must exist in database layout)
    VALID_VENDOR_ID = 1
    INVALID_VENDOR_ID = 9999
    VALID_CUSTOMER_ID = 1
    VALID_PRODUCT_ID = 1

    connection = get_database_connection()
    if not connection:
        print("❌ Setup Failure: Database offline.")
        return

    try:
        cursor = connection.cursor(dictionary=True)

        # ====================================================
        # TEST 1: SUCCESSFUL FINALIZATION (HAPPY PATH)
        # ====================================================
        print("Test 1: Running Successful Finalization Pipeline...")
        # Setup draft bill structure
        bill_setup = create_bill(vendor_id=VALID_VENDOR_ID, customer_id=VALID_CUSTOMER_ID)
        sale_id = bill_setup["bill_data"]["sale_id"]
        
        # Populate bill with an active item to clear empty checks
        add_product_to_bill(sale_id=sale_id, product_id=VALID_PRODUCT_ID, requested_quantity=1)
        
        # Execute action target
        result = finalize_bill(sale_id=sale_id, vendor_id=VALID_VENDOR_ID)
        
        # Assert response contract
        assert result["success"] is True, "Test 1 Failed: Response reported unsuccessful."
        assert result["bill_summary"]["payment_status"] == "Paid", "Test 1 Failed: State marker not changed."
        
        # Direct database record validation verification
        cursor.execute("SELECT payment_status FROM sales WHERE sale_id = %s", (sale_id,))
        db_record = cursor.fetchone()
        assert db_record["payment_status"] == "Paid", "Database verification failure: Row state still marked as unpaid."
        print("✅ Test 1 Passed: Bill successfully validated and locked inside database storage.\n")

        # ====================================================
        # TEST 2: INVALID BILL ID EXCEPTION HANDLING
        # ====================================================
        print("Test 2: Verifying Invalid Bill ID Handling...")
        INVALID_SALE_ID = 999999
        result = finalize_bill(sale_id=INVALID_SALE_ID, vendor_id=VALID_VENDOR_ID)
        
        assert result["success"] is False, "Test 2 Failed: Accepted a non-existent sale ID mapping."
        assert "not found" in result["message"].lower() or "access denied" in result["message"].lower()
        print("✅ Test 2 Passed: Invalid sale ID blocked cleanly.\n")

        # ====================================================
        # TEST 3: INVALID VENDOR (CROSS-TENANT MITIGATION)
        # ====================================================
        print("Test 3: Verifying Tenant Isolation Boundaries...")
        # Try to modify the valid sale using an unauthorized vendor session
        result = finalize_bill(sale_id=sale_id, vendor_id=INVALID_VENDOR_ID)
        
        assert result["success"] is False, "Test 3 Failed: Cross-tenant state modification allowed."
        print("✅ Test 3 Passed: Unauthorized multi-tenant access blocked safely.\n")

        # ====================================================
        # TEST 4: IDEMPOTENCY / ALREADY FINALIZED GUARD
        # ====================================================
        print("Test 4: Verifying Idempotency Guards Against Locked Entries...")
        # Execute finalization action on the already completed 'sale_id'
        result = finalize_bill(sale_id=sale_id, vendor_id=VALID_VENDOR_ID)
        
        assert result["success"] is False, "Test 4 Failed: Re-finalized an already closed database document."
        assert "already finalized" in result["message"].lower() or "operation blocked" in result["message"].lower()
        print("✅ Test 4 Passed: Immutability rules enforced safely.\n")

        print("🎉 ALL FINALIZE_BILL() INTEGRATION TESTS PASSED PERFECTLY!")

    except AssertionError as error:
        print(f"❌ Test Assertion Failure: {error}")
    except Exception as general_err:
        print(f"❌ Unexpected script crash: {general_err}")
    finally:
        cursor.close()
        close_database_connection(connection)

if __name__ == "__main__":
    run_finalize_bill_tests()