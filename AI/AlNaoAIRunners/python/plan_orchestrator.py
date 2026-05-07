import os
import re
from datetime import datetime
from python.database import Plan, Task, db_session
from python.single_step_runner import SingleStepRunner
from python.git_manager import GitManager
from python.logger import get_logger

logger = get_logger(__name__)

def slugify(text):
    if not text: return "unnamed"
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

class PlanOrchestrator:
    def __init__(self, repo_url: str, workspace_dir: str, logs_path: str):
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir
        self.logs_path = logs_path

    def _log(self, plan_id: str, msg: str, title: str = None):
        slug_title = slugify(title)
        plan_folder = f"plan-{slug_title}-{plan_id}"
        plan_logs_dir = os.path.join(self.logs_path, plan_folder)
        os.makedirs(plan_logs_dir, exist_ok=True)
        orchestrator_log = os.path.join(plan_logs_dir, "worker.log")
        with open(orchestrator_log, "a") as f:
            f.write(f"[{datetime.utcnow().isoformat()}] {msg}\n")
        logger.info(f"[{plan_id}] {msg}")

    def execute_plan(self, plan_id: str):
        plan = db_session.query(Plan).get(plan_id)
        if not plan:
            return

        plan.status = 'RUNNING'
        db_session.commit()
        
        slug_title = slugify(plan.title)
        plan_folder = f"plan-{slug_title}-{plan.id}"

        def log_cb(msg):
            self._log(plan.id, msg, title=plan.title)
            
        # Ensure workspace is a subfolder of base_dir to avoid "not a git repo" on base_dir itself
        workspace_dir_name = os.getenv('REPO_WORKSPACE_DIR_NAME', 'workspace')
        base_path = plan.base_dir if plan.base_dir else self.workspace_dir
        workspace_path = os.path.join(base_path, workspace_dir_name)
        
        git = GitManager(self.repo_url, workspace_path, log_cb)
        runner = SingleStepRunner(workspace_path, self.logs_path, log_cb, plan_folder=plan_folder, plan_title=plan.title)
        
        self._log(plan.id, "Plan started. Cloning branch...", title=plan.title)

        try:
            git.clone_or_pull(plan.branch)
            self._log(plan_id, f"Branch {plan.branch} cloned/pulled.")

            tasks = db_session.query(Task).filter_by(plan_id=plan.id)\
                .filter(Task.status.in_(['PENDING', 'WAITING_CREDITS']))\
                .order_by(Task.step_order).all()

            for task in tasks:
                self._log(plan_id, f"Executing Step {task.step_order} with agent {task.agent}...")
                task.status = 'RUNNING'
                db_session.commit()

                result = runner.run_task(task.id)

                if result['status'] == 'WAITING_CREDITS':
                    self._log(plan_id, f"Step {task.step_order} hit rate limit.")
                    plan.status = 'WAITING_CREDITS'
                    db_session.commit()
                    return

                if result['status'] == 'FAILED':
                    self._log(plan_id, f"Step {task.step_order} failed.")
                    plan.status = 'FAILED'
                    db_session.commit()
                    return

                full_commit_msg = f"{plan.commit_prefix or 'Auto-commit'}: {task.commit_msg or ''} (Plan: {plan.id}, Step: {task.step_order})"
                commit_hash = git.commit_step(full_commit_msg)
                task.last_commit_hash = commit_hash
                db_session.commit()
                self._log(plan_id, f"Step {task.step_order} completed. Commit: {commit_hash}")

            import shutil
            self._log(plan_id, "All tasks complete. Copying logs to repo...", title=plan.title)
            
            agent_logs_dir_name = os.getenv('REPO_AGENT_LOGS_DIR', '.alNaoAgentLogs')
            repo_logs_dir = os.path.join(workspace_path, agent_logs_dir_name, f"plan-{slug_title}")
            os.makedirs(repo_logs_dir, exist_ok=True)
            
            plan_logs_dir = os.path.join(self.logs_path, plan_folder)
            
            if os.path.exists(plan_logs_dir):
                for f in os.listdir(plan_logs_dir):
                    if f.endswith('.md') or f == 'worker.log':
                        shutil.copy2(os.path.join(plan_logs_dir, f), repo_logs_dir)
            
            git.commit_step(f"plan-{slug_title}-report")
            
            self._log(plan_id, "Logs committed. Pushing branch...", title=plan.title)
            git.push(plan.branch)
            plan.status = 'COMPLETED'
            db_session.commit()
            self._log(plan_id, "Plan execution finished successfully.")

        except Exception as e:
            plan.status = 'FAILED'
            db_session.commit()
            self._log(plan_id, f"Plan failed with exception: {str(e)}")
