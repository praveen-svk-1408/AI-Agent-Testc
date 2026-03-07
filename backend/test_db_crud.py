from app.database import SessionLocal
from app.models import TestSuite, TestCase

# Create a session
session = SessionLocal()

# Test UPDATE operation
suite = session.query(TestSuite).filter(TestSuite.id == 1).first()
if suite:
    print(f"✓ Before Update:")
    print(f"  Name: {suite.name}")
    print(f"  Description: {suite.description}")
    
    # Update the suite
    suite.description = "Updated description: Test cases for login and logout functionality"
    session.commit()
    
    print(f"\n✓ After Update:")
    print(f"  Name: {suite.name}")
    print(f"  Description: {suite.description}")
    print(f"  Updated at: {suite.updated_at}")

# Test CREATE operation
new_suite = TestSuite(
    name="Checkout Feature Tests",
    base_url="http://localhost:3000/checkout",
    description="Test cases for checkout and payment flow"
)
session.add(new_suite)
session.commit()

print(f"\n✓ New TestSuite Created:")
print(f"  ID: {new_suite.id}")
print(f"  Name: {new_suite.name}")
print(f"  Base URL: {new_suite.base_url}")
print(f"  Description: {new_suite.description}")

# Verify both suites exist
suites = session.query(TestSuite).all()
print(f"\n✓ Total TestSuites in database: {len(suites)}")
for suite in suites:
    print(f"  - {suite.name} (ID: {suite.id})")

session.close()
print("\n✓ Database CRUD operations verified!")
