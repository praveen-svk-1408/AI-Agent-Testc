from app.database import SessionLocal
from app.models import TestSuite, TestCase, TestStep

session = SessionLocal()

# Get the E-commerce test suite
suite = session.query(TestSuite).filter(TestSuite.name == "E-commerce site").first()

if suite:
    print("\n" + "="*60)
    print("TEST SUITE DETAILS")
    print("="*60)
    print(f"Suite ID: {suite.id}")
    print(f"Suite Name: {suite.name}")
    print(f"Base URL: {suite.base_url}")
    print(f"Description: {suite.description}")
    print(f"Created: {suite.created_at}")
    print(f"Updated: {suite.updated_at}")
    
    # Get test cases for this suite
    cases = session.query(TestCase).filter(TestCase.suite_id == suite.id).all()
    print(f"\n{'─'*60}")
    print(f"TEST CASES ({len(cases)} total)")
    print(f"{'─'*60}")
    
    for case in cases:
        print(f"\nCase ID: {case.id}")
        print(f"Case Name: {case.name}")
        print(f"Path: {case.path}")
        print(f"Description: {case.description}")
        print(f"Created: {case.created_at}")
        
        # Get steps for this case
        steps = session.query(TestStep).filter(TestStep.case_id == case.id).order_by(TestStep.order).all()
        print(f"\n  TEST STEPS ({len(steps)} total):")
        print(f"  {'-'*56}")
        
        for step in steps:
            print(f"\n  Step {step.order}: {step.action_type.value.upper()}")
            print(f"    Description: {step.description}")
            if step.target_selector:
                print(f"    Selector: {step.target_selector}")
            if step.value:
                print(f"    Value: {step.value}")
            if step.expected_result:
                print(f"    Expected: {step.expected_result}")
            print(f"    ID: {step.id}")

print("\n" + "="*60)
print("✅ DATABASE VERIFICATION COMPLETE")
print("="*60)

session.close()
