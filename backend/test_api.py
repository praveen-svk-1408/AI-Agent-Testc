import requests
import json
import time

# Wait for server to be ready
time.sleep(2)

BASE_URL = "http://localhost:8000/api"

# Colors for output
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}→ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

# Step 1: Create Test Suite
print_info("Creating Test Suite: E-commerce site")
suite_data = {
    "name": "E-commerce site",
    "base_url": "http://localhost:3000",
    "description": "Test cases for e-commerce application login functionality"
}

response = requests.post(f"{BASE_URL}/test-suites", json=suite_data)
if response.status_code == 201:
    suite = response.json()
    suite_id = suite["id"]
    print_success(f"Test Suite created: ID={suite_id}, Name={suite['name']}")
else:
    print_error(f"Failed to create test suite: {response.status_code}")
    print(response.text)
    exit(1)

# Step 2: Create Test Case
print_info("\nCreating Test Case: Test Login")
case_data = {
    "suite_id": suite_id,
    "path": "/login",
    "name": "Test Login",
    "description": "Test login page with valid credentials - email: test@example.com, password: password123. Expected: user must login and redirect to dashboard page"
}

response = requests.post(f"{BASE_URL}/test-cases", json=case_data)
if response.status_code == 201:
    case = response.json()
    case_id = case["id"]
    print_success(f"Test Case created: ID={case_id}, Name={case['name']}")
else:
    print_error(f"Failed to create test case: {response.status_code}")
    print(response.text)
    exit(1)

# Step 3: Create Test Steps
print_info("\nCreating Test Steps for login flow:")

steps = [
    {
        "action_type": "navigate",
        "value": "http://localhost:3000/login",
        "order": 1,
        "description": "Navigate to login page"
    },
    {
        "action_type": "fill",
        "target_selector": "input[name='email']",
        "value": "test@example.com",
        "order": 2,
        "description": "Enter email address"
    },
    {
        "action_type": "fill",
        "target_selector": "input[name='password']",
        "value": "password123",
        "order": 3,
        "description": "Enter password"
    },
    {
        "action_type": "click",
        "target_selector": "button[type='submit']",
        "order": 4,
        "description": "Click login button"
    },
    {
        "action_type": "assert",
        "expected_result": "url contains '/dashboard'",
        "order": 5,
        "description": "Verify redirect to dashboard page"
    }
]

step_ids = []
for step in steps:
    step_data = {
        "case_id": case_id,
        **step
    }
    response = requests.post(f"{BASE_URL}/test-steps", json=step_data)
    if response.status_code == 201:
        created_step = response.json()
        step_ids.append(created_step["id"])
        print_success(f"  Step {step['order']}: {step['description']} (ID={created_step['id']})")
    else:
        print_error(f"Failed to create step: {response.status_code}")
        print(response.text)
        exit(1)

# Step 4: Verify by fetching the test case with all steps
print_info("\nVerifying created test case with all steps:")
response = requests.get(f"{BASE_URL}/test-cases/{case_id}")
if response.status_code == 200:
    case_detail = response.json()
    print_success(f"Test Case: {case_detail['name']}")
    print(f"  Path: {case_detail['path']}")
    print(f"  Description: {case_detail['description']}")
    print(f"  Total Steps: {len(case_detail.get('steps', []))}")
    
    for step in case_detail.get('steps', []):
        action = step['action_type']
        order = step['order']
        desc = step['description']
        selector = step.get('target_selector', 'N/A')
        value = step.get('value', 'N/A')
        
        print(f"\n  Step {order}: {action.upper()}")
        print(f"    Description: {desc}")
        if selector != 'N/A':
            print(f"    Selector: {selector}")
        if value != 'N/A':
            print(f"    Value: {value}")
else:
    print_error(f"Failed to fetch test case: {response.status_code}")

# Step 5: Get Test Suite details
print_info("\nFinal Test Suite Summary:")
response = requests.get(f"{BASE_URL}/test-suites/{suite_id}")
if response.status_code == 200:
    suite_detail = response.json()
    print_success(f"Suite: {suite_detail['name']} (ID={suite_detail['id']})")
    print(f"  Base URL: {suite_detail['base_url']}")
    print(f"  Description: {suite_detail['description']}")
    print(f"  Created at: {suite_detail['created_at']}")
    print(f"  Updated at: {suite_detail['updated_at']}")

print_success("\n✅ Backend API test completed successfully!")
print(f"\nAPI Endpoints:")
print(f"  Swagger UI: http://localhost:8000/docs")
print(f"  ReDoc: http://localhost:8000/redoc")
