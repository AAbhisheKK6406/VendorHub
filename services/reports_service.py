from mysql.connector import Error
from database.db import get_database_connection, close_database_connection
from datetime import datetime, timedelta

def generate_sales_summary(vendor_id):
    """
    Aggregates point-of-sale metrics to generate a high-level 
    financial health summary for a specific vendor.
    
    Args:
        vendor_id (int): The unique database identifier of the target vendor.
        
    Returns:
        dict: Operational status flag along with the structured report payload.
    """
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "report_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "report_data": None}

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. Verify Vendor Existence
        vendor_check_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_check_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Access Denied: Vendor profile not found.", "report_data": None}

        # 2. Compute Aggregated Operational Header Metrics
        # Treats Paid or Completed sales as valid revenue contributors
        metrics_query = """
            SELECT 
                COUNT(sale_id) as total_sales,
                COALESCE(SUM(total_amount), 0.0) as total_revenue
            FROM sales
            WHERE vendor_id = %s AND payment_status IN ('Paid', 'Completed', 'Unpaid')
        """
        cursor.execute(metrics_query, (vendor_id,))
        summary_metrics = cursor.fetchone()

        # 3. Compute Total Quantity of Products Sold
        products_sold_query = """
            SELECT COALESCE(SUM(si.quantity), 0) as total_units
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.vendor_id = %s
        """
        cursor.execute(products_sold_query, (vendor_id,))
        items_metrics = cursor.fetchone()

        # 4. Extract Metrics and Format Mathematical Variables
        total_sales = int(summary_metrics["total_sales"])
        total_revenue = float(summary_metrics["total_revenue"])
        total_products_sold = int(items_metrics["total_units"])
        
        # Calculate Average Bill Value safely to prevent DivisionByZero exceptions
        average_bill_value = float(total_revenue / total_sales) if total_sales > 0 else 0.0

        # 5. Build Structured Summary Contract Payload
        report_payload = {
            "vendor_id": vendor_id,
            "metrics": {
                "total_completed_sales": total_sales,
                "total_revenue": total_revenue,
                "total_products_sold": total_products_sold,
                "average_bill_value": round(average_bill_value, 2)
            }
        }

        return {
            "success": True,
            "message": "Sales summary report successfully generated.",
            "report_data": report_payload
        }

    except Error as db_error:
        return {"success": False, "message": f"Database reporting module error: {db_error}", "report_data": None}

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)



def generate_sales_report(vendor_id, report_type):
    """
    Generates a filtered financial performance report over a designated 
    time window (daily, weekly, monthly) for an explicit vendor.
    
    Args:
        vendor_id (int): The unique database identifier of the target vendor.
        report_type (str): The time interval frame ('daily', 'weekly', 'monthly').
        
    Returns:
        dict: Operational status status flag alongside the structured report data.
    """
    # 1. Input Sanitization and Validations
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "report_data": None}
        
    if not report_type or report_type.lower() not in ['daily', 'weekly', 'monthly']:
        return {"success": False, "message": "Validation Failure: Invalid or unsupported report period frame.", "report_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "report_data": None}

    try:
        cursor = connection.cursor(dictionary=True)
        report_type = report_type.lower()

        # 2. Verify Vendor Profile Existence Boundary
        vendor_check_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_check_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Access Denied: Vendor profile not found.", "report_data": None}

        # 3. Formulate SQL Interval Mappings Dynamically
        if report_type == 'daily':
            date_filter = "s.sale_date >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
        elif report_type == 'weekly':
            date_filter = "s.sale_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        else:  # monthly
            date_filter = "s.sale_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)"

        # 4. Compute Financial Metrics inside Time Window using a single optimized pass
        metrics_query = f"""
            SELECT 
                COUNT(DISTINCT s.sale_id) as total_bills,
                COALESCE(SUM(s.total_amount), 0.0) as total_revenue,
                COALESCE(SUM(si.quantity), 0) as total_products
            FROM sales s
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE s.vendor_id = %s 
              AND s.payment_status IN ('Paid', 'Completed', 'Unpaid')
              AND {date_filter}
        """
        cursor.execute(metrics_query, (vendor_id,))
        report_metrics = cursor.fetchone()

        # 5. Extract Metrics and Cast to Safe Types
        total_bills = int(report_metrics["total_bills"])
        total_revenue = float(report_metrics["total_revenue"])
        total_products_sold = int(report_metrics["total_products"])
        
        # ZeroDivision safety fallback rule logic checking
        average_bill_value = float(total_revenue / total_bills) if total_bills > 0 else 0.0

        # 6. Build Standard Report Contract Structure
        report_payload = {
            "vendor_id": vendor_id,
            "report_type": report_type,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {
                "total_completed_bills": total_bills,
                "total_revenue": total_revenue,
                "total_products_sold": total_products_sold,
                "average_bill_value": round(average_bill_value, 2)
            }
        }

        return {
            "success": True,
            "message": f"Periodic {report_type} sales report successfully generated.",
            "report_data": report_payload
        }

    except Error as db_error:
        return {"success": False, "message": f"Database reporting exception running periodic summary: {db_error}", "report_data": None}

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)

from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def generate_top_selling_products(vendor_id, limit=10):
    """
    Identifies and aggregates performance data for a vendor's highest-velocity
    products based on historical finalized sales records.
    
    Args:
        vendor_id (int): The unique database identifier of the target vendor.
        limit (int): The maximum number of product records to return. Defaults to 10.
        
    Returns:
        dict: Standard operational success status alongside the structured report data payload.
    """
    # 1. Input Validation Threshold Check
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "report_data": None}
        
    try:
        limit = int(limit)
        if limit <= 0:
            return {"success": False, "message": "Validation Failure: Limit must be a positive integer.", "report_data": None}
    except (ValueError, TypeError):
        return {"success": False, "message": "Validation Failure: Limit must be a valid integer conversion candidate.", "report_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "report_data": None}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Verify Vendor Profile Existence Boundary
        vendor_check_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_check_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Access Denied: Vendor profile not found.", "report_data": None}

        # 3. Compile Aggregated Top Products using a Multi-Table Relational Join
        top_products_query = """
            SELECT 
                si.product_id,
                COALESCE(p.product_name, CONCAT('Product #', si.product_id)) as product_name,
                SUM(si.quantity) as total_quantity_sold,
                SUM(si.subtotal) as total_revenue_generated
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            LEFT JOIN products p ON si.product_id = p.product_id
            WHERE s.vendor_id = %s 
              AND s.payment_status IN ('Paid', 'Completed', 'Unpaid')
            GROUP BY si.product_id, p.product_name
            ORDER BY total_quantity_sold DESC, total_revenue_generated DESC
            LIMIT %s
        """
        cursor.execute(top_products_query, (vendor_id, limit))
        product_records = cursor.fetchall()

        # 4. Standardize and Format Result Records
        formatted_products = []
        for row in product_records:
            formatted_products.append({
                "product_id": int(row["product_id"]),
                "product_name": row["product_name"],
                "total_quantity_sold": int(row["total_quantity_sold"]),
                "total_revenue_generated": round(float(row["total_revenue_generated"]), 2)
            })

        # 5. Build Final Standardized Report Contract Payload
        report_payload = {
            "vendor_id": vendor_id,
            "items_returned_count": len(formatted_products),
            "top_products": formatted_products
        }

        return {
            "success": True,
            "message": "Top selling products report successfully generated.",
            "report_data": report_payload
        }

    except Error as db_error:
        return {"success": False, "message": f"Database reporting module error: {db_error}", "report_data": None}

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)

from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def generate_low_stock_report(vendor_id):
    """
    Identifies and profiles inventory products that have depleted below or equal
    to their designated low stock threshold limits.
    
    Args:
        vendor_id (int): The unique database identifier of the target vendor.
        
    Returns:
        dict: Operational success status alongside the structured report payload.
    """
    # 1. Input Sanitization
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "report_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "report_data": None}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Verify Vendor Profile Existence Boundary
        vendor_check_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_check_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Access Denied: Vendor profile not found.", "report_data": None}

        # 3. Fetch Low Stock Records
        # Compares current quantity against the specific low_stock_limit condition
        low_stock_query = """
            SELECT 
                product_id,
                product_name,
                category,
                quantity,
                low_stock_limit,
                selling_price
            FROM products
            WHERE vendor_id = %s 
              AND quantity <= low_stock_limit
            ORDER BY quantity ASC
        """
        cursor.execute(low_stock_query, (vendor_id,))
        product_records = cursor.fetchall()

        # 4. Format and Standardize Payload Primitive Types
        formatted_report_list = []
        for row in product_records:
            formatted_report_list.append({
                "product_id": int(row["product_id"]),
                "product_name": row["product_name"],
                "category": row["category"] if row["category"] else "General",
                "current_quantity": int(row["quantity"]),
                "low_stock_limit": int(row["low_stock_limit"]) if row["low_stock_limit"] is not None else 0,
                "selling_price": round(float(row["selling_price"]), 2)
            })

        # 5. Build Unified Result Payload Contract Struct
        report_payload = {
            "vendor_id": vendor_id,
            "low_stock_items_count": len(formatted_report_list),
            "low_stock_items": formatted_report_list
        }

        return {
            "success": True,
            "message": "Low stock alert report successfully generated.",
            "report_data": report_payload
        }

    except Error as db_error:
        return {"success": False, "message": f"Database reporting module error: {db_error}", "report_data": None}

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)

from mysql.connector import Error
from database.db import get_database_connection, close_database_connection

def generate_customer_purchase_report(vendor_id):
    """
    Compiles behavioral sales metrics for each customer interacting with 
    the targeted vendor, calculating spending power, volumes, and timelines.
    
    Args:
        vendor_id (int): The unique database identifier of the target vendor.
        
    Returns:
        dict: Operational validation status flag along with the structured report payload.
    """
    # 1. Input Sanitization Check
    if not vendor_id:
        return {"success": False, "message": "Validation Failure: Vendor ID is required.", "report_data": None}

    connection = get_database_connection()
    if not connection:
        return {"success": False, "message": "Database pipeline offline.", "report_data": None}

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Verify Vendor Profile Existence Boundary
        vendor_check_query = "SELECT id FROM vendors WHERE id = %s"
        cursor.execute(vendor_check_query, (vendor_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "Access Denied: Vendor profile not found.", "report_data": None}

        # 3. Aggregate Customer Transactional Profiles via Multi-Table Relational Join
        # Handles missing customer profile labels safely by checking customer_id fallbacks
        customer_report_query = """
            SELECT 
                s.customer_id,
                COALESCE(c.customer_name, 'Walk-in Customer') as customer_name,
                COUNT(DISTINCT s.sale_id) as total_orders,
                SUM(s.total_amount) as total_spent,
                COALESCE(SUM(si.quantity), 0) as total_products,
                MAX(s.sale_date) as last_purchase_date
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE s.vendor_id = %s 
              AND s.payment_status IN ('Paid', 'Completed', 'Unpaid')
            GROUP BY s.customer_id, c.customer_name
            ORDER BY total_spent DESC, total_orders DESC
        """
        cursor.execute(customer_report_query, (vendor_id,))
        customer_records = cursor.fetchall()

        # 4. Normalize and Format Payload Primitive Structures
        formatted_customer_list = []
        for row in customer_records:
            total_orders = int(row["total_orders"])
            total_spent = float(row["total_spent"])
            
            # ZeroDivision safety fallback rule logic checking
            average_order_value = float(total_spent / total_orders) if total_orders > 0 else 0.0

            formatted_customer_list.append({
                "customer_id": int(row["customer_id"]),
                "customer_name": row["customer_name"],
                "total_orders": total_orders,
                "total_amount_spent": round(total_spent, 2),
                "total_products_purchased": int(row["total_products"]),
                "average_order_value": round(average_order_value, 2),
                "last_purchase_date": row["last_purchase_date"].strftime("%Y-%m-%d %H:%M:%S") if row["last_purchase_date"] else "N/A"
            })

        # 5. Build Unified Result Payload Contract Struct
        report_payload = {
            "vendor_id": vendor_id,
            "tracked_customers_count": len(formatted_customer_list),
            "customer_purchases": formatted_customer_list
        }

        return {
            "success": True,
            "message": "Customer purchase analytics report successfully generated.",
            "report_data": report_payload
        }

    except Error as db_error:
        return {"success": False, "message": f"Database reporting module error: {db_error}", "report_data": None}

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        close_database_connection(connection)