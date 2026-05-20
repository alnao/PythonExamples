import os
import re
from datetime import datetime
from python.database import Plan, Task, db_session
from python.single_step_runner import SingleStepRunner
from python.git_manager import GitManager
from python.logger import get_logger

logger = get_logger(__name__)
UNAMED="unnamed"


def slugify(text):
    if not text: return UNAMED
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

class PlanOrchestrator:
    def __init__(self, repo_url: str, workspace_dir: str, logs_path: str):
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir
        self.logs_path = logs_path

    def _log(self, plan_id: str, msg: str, title: str = None):
        slug_title = slugify(title)
        if slug_title==UNAMED:
            return
        plan_folder = f"plan{plan_id}-{slug_title}"
        plan_logs_dir = os.path.join(self.logs_path, plan_folder)
        os.makedirs(plan_logs_dir, exist_ok=True)
        orchestrator_log = os.path.join(plan_logs_dir, f"plan{plan_id}.log")
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
        plan_folder = f"plan{plan.id}-{slug_title}"

        def log_cb(msg):
            self._log(plan.id, msg, title=plan.title)
            
        # Ensure workspace is a subfolder of base_dir to avoid "not a git repo" on base_dir itself
        workspace_dir_name = os.getenv('REPO_WORKSPACE_DIR_NAME', 'workspace')
        base_path = plan.base_dir if plan.base_dir else self.workspace_dir
        workspace_path = os.path.join(base_path, workspace_dir_name)
        
        git = GitManager(self.repo_url, workspace_path, log_cb)
        runner = SingleStepRunner(workspace_path, self.logs_path, log_cb, plan_folder=plan_folder, plan_title=plan.title)
        
        main_branch = plan.branch
        work_branch = plan.work_branch or os.getenv('WORK_BRANCH', 'alnao-ai-agent')
        agent_logs_dir_name = os.getenv('REPO_AGENT_LOGS_DIR', '.alNaoAgentLogs')
        repo_logs_dir = os.path.join(workspace_path, agent_logs_dir_name, f"plan{plan_id}-{slug_title}")

        self._log(plan.id, f"Plan started. Main branch: {main_branch}, Work branch: {work_branch}", title=plan.title)

        try:
            # Step 1: Clone/pull the main branch
            self._log(plan_id, f"Cloning/pulling main branch '{main_branch}'...")
            git.clone_or_pull(main_branch)
            self._log(plan_id, f"Main branch '{main_branch}' ready.")

            # Step 2: Setup work branch (create or sync with main)
            self._log(plan_id, f"Setting up work branch '{work_branch}'...")
            git.setup_work_branch(main_branch, work_branch)
            self._log(plan_id, f"Work branch '{work_branch}' ready.")

            # Step 3: Execute tasks on the work branch
            tasks = db_session.query(Task).filter_by(plan_id=plan.id)\
                .filter(Task.status.in_(['PENDING', 'WAITING_CREDITS']))\
                .order_by(Task.step_order).all()

            for task in tasks:
                self._log(plan_id, f"--------------------------------------------------------------------------")                    
                self._log(plan_id, f"Executing Step {task.step_order} with agent {task.agent}...")
                task.status = 'RUNNING'
                db_session.commit()

                result = runner.run_task(task.id)

                if result['status'] == 'WAITING_CREDITS':

                    self._log(plan_id, f"Step {task.step_order} hit rate limit. retring in 1 minute")

                    plan.status = 'WAITING_CREDITS'
                    db_session.commit()
                    return

                if result['status'] == 'FAILED':
                    self._log(plan_id, f"Step {task.step_order} failed.")
                    plan.status = 'FAILED'
                    db_session.commit()
                    return

                if task.commit_after_task:
                    prefix = f"{plan.commit_prefix}: " if plan.commit_prefix else ""
                    suffix = plan.commit_suffix or ""
                    full_commit_msg = f"{prefix}{task.commit_msg or ''}{suffix}"
                    commit_hash = git.commit_step(full_commit_msg)
                    task.last_commit_hash = commit_hash
                    db_session.commit()
                    self._log(plan_id, f"Step {task.step_order} completed. Commit: {commit_hash}")
                else:
                    self._log(plan_id, f"Step {task.step_order} completed. (No commit executed as requested)")

                # Apply inter-task delay if there are more tasks to run
                if task != tasks[-1]:
                    delay = plan.task_delay_seconds if plan.task_delay_seconds is not None else int(os.getenv('TASK_DELAY_SECONDS', 30))
                    if delay > 0:
                        self._log(plan_id, f"Waiting {delay} seconds before next task...")
                        import time
                        time.sleep(delay)

            # Step 4: Copy logs to repo
            import shutil
            self._log(plan_id, "All tasks complete. Logging overall modified files and copying logs to repo...", title=plan.title)
            
            # Get all modified files since main branch
            diff_res = git._run_soft(['git', '-C', workspace_path, 'diff', f'origin/{main_branch}', 'HEAD', '--name-status'])
            diff_output = diff_res.stdout.strip() if diff_res.returncode == 0 else ""
            if diff_output:
                self._log(plan_id, f"Overall files modified/added/removed in this plan:\n{diff_output}", title=plan.title)
            else:
                self._log(plan_id, "No files modified/added/removed in this plan.", title=plan.title)
                
            repo_logs_dir = os.path.join(workspace_path, agent_logs_dir_name, f"plan-{slug_title}")
            os.makedirs(repo_logs_dir, exist_ok=True)
            plan_logs_dir = os.path.join(self.logs_path, plan_folder)
            if os.path.exists(plan_logs_dir):
                for f in os.listdir(plan_logs_dir):
                    if f.startswith('worker.log') or f.endswith(f".log"): # or f.endswith('.md'):
                        shutil.copy2(os.path.join(plan_logs_dir, f), repo_logs_dir)
            
            prefix = f"{plan.commit_prefix}: " if plan.commit_prefix else ""
            suffix = plan.commit_suffix or ""
            report_commit_msg = f"{prefix} final report {suffix}"
            git.commit_step(report_commit_msg)
            
            # Step 5: Push only the work branch if requested
            if plan.push_final:
                self._log(plan_id, f"Logs committed. Pushing work branch '{work_branch}'...", title=plan.title)
                git.push(work_branch)
            else:
                self._log(plan_id, f"Logs committed. (Pushing work branch skipped as requested)", title=plan.title)
            plan.status = 'COMPLETED'
            db_session.commit()
            self._log(plan_id, "Plan execution finished successfully.")

        except Exception as e:
            plan.status = 'FAILED'
            db_session.commit()
            self._log(plan_id, f"Plan failed with exception: {str(e)}")

