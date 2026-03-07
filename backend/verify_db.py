from app.database import SessionLocal
from app.models import TestSuite, TestCase, TestStep

# Create a session
session = SessionLocal()

# Query all data
suites = session.query(TestSuite).all()
print("✓ TestSuites:")
for suite in suites:
    print(f"  - {suite.name} (ID: {suite.id})")
    print(f"    Base URL: {suite.base_url}")
    print(f"    Description: {suite.description}")
    
    cases = session.query(TestCase).filter(TestCase.suite_id == suite.id).all()
    for case in cases:
        print(f"    - Case: {case.name} (ID: {case.id})")
        steps = session.query(TestStep).filter(TestStep.case_id == case.id).order_by(TestStep.order).all()
        print(f"      Steps: {len(steps)}")
        for step in steps:
            print(f"        {step.order}. {step.action_type.value} - {step.description}")

session.close()
print("\n✓ Database content verified!")
