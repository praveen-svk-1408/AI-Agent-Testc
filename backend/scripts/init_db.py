"""
Database initialization script.
Creates database tables and seeds sample data.
"""

import sys
from app.database import Base, engine, SessionLocal
from app.models import TestSuite, TestCase, TestStep, ActionType


def init_db():
    """Initialize database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")


def seed_db():
    """Seed sample data into the database."""
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_suites = db.query(TestSuite).count()
        if existing_suites > 0:
            print("✓ Database already contains data, skipping seed")
            return
        
        print("Seeding sample data...")
        
        # Create sample test suite
        suite = TestSuite(
            name="Login Feature Tests",
            base_url="http://localhost:3000",
            description="Test cases for login functionality",
        )
        db.add(suite)
        db.flush()  # Flush to get the ID
        
        # Create sample test case
        test_case = TestCase(
            suite_id=suite.id,
            path="/login",
            name="Successful Login",
            description="Test successful login with valid credentials",
        )
        db.add(test_case)
        db.flush()
        
        # Create sample test steps
        steps = [
            TestStep(
                case_id=test_case.id,
                action_type=ActionType.NAVIGATE,
                target_selector=None,
                value="http://localhost:3000/login",
                expected_result=None,
                order=1,
                description="Navigate to login page",
            ),
            TestStep(
                case_id=test_case.id,
                action_type=ActionType.FILL,
                target_selector="input[name='email']",
                value="test@example.com",
                expected_result=None,
                order=2,
                description="Enter email address",
            ),
            TestStep(
                case_id=test_case.id,
                action_type=ActionType.FILL,
                target_selector="input[name='password']",
                value="password123",
                expected_result=None,
                order=3,
                description="Enter password",
            ),
            TestStep(
                case_id=test_case.id,
                action_type=ActionType.CLICK,
                target_selector="button[type='submit']",
                value=None,
                expected_result=None,
                order=4,
                description="Click login button",
            ),
            TestStep(
                case_id=test_case.id,
                action_type=ActionType.ASSERT,
                target_selector=None,
                value=None,
                expected_result="url contains '/dashboard'",
                order=5,
                description="Verify redirect to dashboard",
            ),
        ]
        
        for step in steps:
            db.add(step)
        
        db.commit()
        print("✓ Sample data seeded successfully")
        
        # Display created data
        print("\nCreated:")
        print(f"  - TestSuite: {suite.name} (ID: {suite.id})")
        print(f"  - TestCase: {test_case.name} (ID: {test_case.id})")
        print(f"  - TestSteps: {len(steps)}")
        
    except Exception as e:
        print(f"✗ Error seeding database: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    init_db()
    seed_db()
    print("\n✓ Database initialization complete!")
