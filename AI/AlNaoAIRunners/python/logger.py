from werkzeug._internal import _log
from asyncio import Task
from python.database import Plan
import logging
import os

LOGS_PATH = os.getenv('LOGS_PATH', '.AlNaoAgent/logs')
os.makedirs(LOGS_PATH, exist_ok=True)
global_log_file = os.path.join(LOGS_PATH, 'application.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(global_log_file),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)

def log_plan(logger:callable,plan:Plan,tasks:list[Task]):
    plan_info = (
        f"=== INITIAL PLAN DETAILS ===\n"
        f"ID: {plan.id}\n"
        f"Title: {plan.title}\n"
        f"Branch: {plan.branch}\n"
        f"Schedule Time: {plan.schedule_time}\n"
        f"Base Dir: {plan.base_dir}\n"
        f"Repo URL: {plan.repo_url}\n"
        f"Work Branch: {plan.work_branch}\n"
        f"Commit Prefix: {plan.commit_prefix}\n"
        f"Commit Suffix: {plan.commit_suffix}\n"
        f"Push Final: {plan.push_final}\n"
        f"Clean Base Dir: {plan.clean_base_dir}\n"
        f"Common Message: {plan.common_message}\n"
        f"Task Delay Seconds: {plan.task_delay_seconds}\n"
        f"Status: {plan.status}\n"
        f"Created At: {plan.created_at}\n\n"
        f"=== TASKS LIST ({len(tasks)} tasks) ===\n"
    )
    for t in tasks:
        plan_info += (
            f"  - Step: {t.step_order} (ID: {t.id})\n"
            f"    Agent: {t.agent}\n"
            f"    Model: {t.model}\n"
            f"    Prompt: {t.prompt}\n"
            f"    Commit Msg: {t.commit_msg}\n"
            f"    Commit After Task: {t.commit_after_task}\n"
            f"    Status: {t.status}\n"
            f"    Last Commit Hash: {t.last_commit_hash}\n"
            f"----------------------------------------\n"
        )
    plan_info += f"\n========================================\n"
    logger(plan.id, plan_info, title=plan.title)