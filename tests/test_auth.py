from services.auth_service import register_vendor, login_vendor
import random

def run_auth_tests():
    print("--- STARTING AUTHENTICATION SERVICE TEST ---")
    
    # Generate a random suffix so running this test multiple times doesn't trigger unique constraint collisions
    unique_id = random.randint(1000, 9999)
    test_user = f"vendor_{unique_id}"
    test_email = f"info_{unique_id}@hub.com"
    test_pass = "SecurePass123"
    
    # 1. TEST REGISTRATION
    print("\nExecuting Test 1: Registering a new vendor...")
    reg_result = register_vendor(
        username=test_user,
        email=test_email,
        password=test_pass,
        business_name="Global Supply Corp",
        phone="+1234567890"
    )
    print(f"Registration Output: {reg_result}")

    # 2. TEST LOGIN WITH CORRECT CREDENTIALS
    print("\nExecuting Test 2: Attempting login with CORRECT credentials...")
    login_success = login_vendor(username_or_email=test_user, password=test_pass)
    print(f"Login Output: {login_success}")
    if login_success["success"]:
        print("-> Connected Successfully!")

    # 3. TEST LOGIN WITH WRONG PASSWORD
    print("\nExecuting Test 3: Attempting login with WRONG password...")
    login_fail = login_vendor(username_or_email=test_user, password="WrongPassword999")
    print(f"Login Output: {login_fail}")

if __name__ == "__main__":
    run_auth_tests()