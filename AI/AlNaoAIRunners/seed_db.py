import uuid
import os
from datetime import datetime
from python.database import Plan, Task, db_session, init_db

def seed():
    print("Seeding database with test data...")
    # Clean previous
    db_session.query(Task).delete()
    db_session.query(Plan).delete()

    plan_id = f"plan-{str(uuid.uuid4())[:8]}"
    p = Plan(
        id=plan_id, 
        title="Test Runner Plan",
        branch="feature/test-runner", 
        schedule_time=datetime.utcnow(), 
        status="PENDING"
    )
    db_session.add(p)
    
    t1 = Task(
        plan_id=plan_id, 
        step_order=1, 
        agent="Analyst", 
        model="claude", 
        prompt="Analyze requirements for test", 
        status="PENDING"
    )
    t2 = Task(
        plan_id=plan_id, 
        step_order=2, 
        agent="Developer", 
        model="gemini", 
        prompt="Write the mock code", 
        status="PENDING"
    )
    db_session.add(t1)
    db_session.add(t2)
    
    db_session.commit()
    print(f"Database seeded. 1 Plan ({plan_id}), 2 Tasks.")

if __name__ == "__main__":
    seed()
