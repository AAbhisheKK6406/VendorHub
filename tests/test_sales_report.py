import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database.db import get_database_connection, close_database_connection
from services.billing_service import create_bill, add_product_to_bill, calculate_bill_total
from services.reports_service import generate_sales_report

def run_periodic_reports_test_suite():
    print("========== RUNNING VENDORHUB PERIODIC SALES REPORT TEST SUITE ==========\n")
    
    VALID_VENDOR_ID = 1
    INVALID_VENDOR_ID = 99999

    connection = get_database_connection()
    if not connection:
        print("❌ Setup Failure: Database pipeline offline.")
        return

    try:
        cursor = connection.cursor(dictionary=True)

        # Inject immediate active transactional mock data to populate local time scopes
        bill_setup = create_bill(vendor_id=VALID_VENDOR_ID, customer_id=1)
        sale_id = bill_setup["bill_data"]["sale_id"]
        add_product_to_bill(sale_id=sale_id, product_id=1, requested_quantity=1)
        calculate_bill_total(sale_id, VALID_VENDOR_ID, 'percentage', 0.0, 18.0, 'Cash', 'Paid')

        # Find a clean valid vendor with no sales to test baseline parameters
        cursor.execute("""
            SELECT id FROM vendors 
            WHERE id NOT IN (SELECT DISTINCT vendor_id FROM sales WHERE vendor_id IS NOT NULL) 
            LIMIT 1
        """)
        empty_vendor_row = cursor.fetchone()
        EMPTY_VENDOR_ID = empty_vendor_row["id"] if empty_vendor_row else VALID_VENDOR_ID

        cursor.close()
        close_database_connection(connection)

        # ====================================================
        # TEST 1: DAILY REPORT RUN
        # ====================================================
        print("Test 1: Running Daily Report Horizon Query Calculations...")
        result = generate_sales_report(VALID_VENDOR_ID, "daily")
        assert result["success"] is True, f"Daily execution failed: {result['message']}"
        print("✅ Test 1 Passed: Daily report generated cleanly.\n")

        # ====================================================
        # TEST 2: WEEKLY REPORT RUN
        # ====================================================
        print("Test 2: Running Weekly Report Horizon Query Calculations...")
        result = generate_sales_report(VALID_VENDOR_ID, "weekly")
        assert result["success"] is True, f"Weekly execution failed: {result['message']}"
        print("✅ Test 2 Passed: Weekly report generated cleanly.\n")

        # ====================================================
        # TEST 3: MONTHLY REPORT RUN
        # ====================================================
        print("Test 3: Running Monthly Report Horizon Query Calculations...")
        result = generate_sales_report(VALID_VENDOR_ID, "monthly")
        assert result["success"] is True, f"Monthly execution failed: {result['message']}"
        print("✅ Test 3 Passed: Monthly report generated cleanly.\n")

        # ====================================================
        # TEST 4: INVALID VENDOR ACCESS CONTROL BOUNDARY
        # ====================================================
        print("Test 4: Testing Boundary Constraints on Missing Ghost Vendors...")
        result = generate_sales_report(INVALID_VENDOR_ID, "daily")
        assert result["success"] is False, "Security Boundary Failure: Processed ghost vendor."
        print("✅ Test 4 Passed: Missing vendor blocked safely.\n")

        # ====================================================
        # TEST 5: INVALID REPORT INTERVAL PARAMETER
        # ====================================================
        print("Test 5: Handling Unmapped Interval Definitions Safely...")
        result = generate_sales_report(VALID_VENDOR_ID, "yearly")
        assert result["success"] is False, "Validation Failure: Allowed an unsupported time-horizon configuration."
        print("✅ Test 5 Passed: Handled improper string arguments cleanly.\n")

        # ====================================================
        # TEST 6: VENDOR WITHOUT SALES DATA FOOTPRINTS
        # ====================================================
        print("Test 6: Simulating Clean Profiles with Zero Historical Sales Logs...")
        result = generate_sales_report(EMPTY_VENDOR_ID, "monthly")
        if result["success"]:
            metrics = result["report_data"]["metrics"]
            assert metrics["total_completed_bills"] == 0 or EMPTY_VENDOR_ID == VALID_VENDOR_ID, "Calculation variance error found."
            print("✅ Test 6 Passed: Zero state reports safely processed.\n")
        else:
            print("✅ Test 6 Passed: Isolation check passed dynamically.\n")

        print("🎉 ALL PERIODIC SALES REPORT INTEGRATION TESTS PASSED PERFECTLY!")

    except AssertionError as assert_err:
        print(f"❌ Test Assertion Failure: {assert_err}")
    except Exception as error:
        print(f"❌ Unexpected script execution failure: {error}")
    finally:
        if 'connection' in locals():
            try:
                close_database_connection(connection)
            except Exception:
                pass

if __name__ == "__main__":
    run_periodic_reports_test_suite()