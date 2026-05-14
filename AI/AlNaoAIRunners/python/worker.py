import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from python.database import Plan, db_session
from python.plan_orchestrator import PlanOrchestrator
from python.logger import get_logger

logger = get_logger(__name__)

load_dotenv()

REPO_URL = os.getenv('REPO_URL', 'mock_repo_url')
WORKSPACE_DIR = os.getenv('WORKSPACE_DIR', '.AlNaoAgent/workspace')
LOGS_PATH = os.getenv('LOGS_PATH', '.AlNaoAgent/logs')

def check_shutdown_condition():
    if os.getenv('AUTO_SHUTDOWN', 'false').lower() == 'true':
        active_plans = db_session.query(Plan).filter(
            Plan.status.in_(['PENDING', 'RUNNING', 'WAITING_CREDITS'])
        ).count()
        if active_plans == 0:
            logger.info("No active plans found. Initiating auto-shutdown...")
            # Uncomment for actual EC2 shutdown
            # os.system('sudo shutdown -h now')

def check_and_run_plans():
    plans = db_session.query(Plan).filter(
        Plan.status.in_(['PENDING', 'WAITING_CREDITS']),
        Plan.schedule_time <= datetime.utcnow()
    ).all()

    for plan in plans:
        logger.info(f"Starting plan {plan.id}...")
        plan_repo_url = plan.repo_url if plan.repo_url else REPO_URL
        orchestrator = PlanOrchestrator(plan_repo_url, WORKSPACE_DIR, LOGS_PATH)
        orchestrator.execute_plan(plan.id)
        
    if not plans:
        check_shutdown_condition()

def start_worker():
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.environ.get('FLASK_ENV'):
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=check_and_run_plans, trigger="interval", minutes=1)
        scheduler.start()
        logger.info("APScheduler worker started. Polling every 1 minute...")
