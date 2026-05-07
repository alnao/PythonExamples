import os
import subprocess
from python.cli_providers import CLIProviderFactory
from python.agent_builder import AgentContextBuilder
from python.database import Task, Log, db_session
from python.logger import get_logger

logger = get_logger(__name__)

class SingleStepRunner:
    def __init__(self, workspace_dir: str, logs_path: str, log_cb, plan_folder: str = None, plan_title: str = None):
        self.workspace_dir = workspace_dir
        self.logs_path = logs_path
        self.plan_folder = plan_folder
        self.plan_title = plan_title
        self.builder = AgentContextBuilder(logs_path,logs_path,plan_folder,plan_title)
        self.max_fix_attempts = 3
        self.log_cb = log_cb

    def slugify(self, text):
        import re
        if not text: return "none"
        return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

    def run_task(self, task_id: int):
        task = db_session.query(Task).get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}

        plan_id = task.plan_id
        cli = CLIProviderFactory.get_provider(task.model)
        
        # Build initial prompt
        prompt = self.builder.build_prompt(plan_id, task.agent, task.prompt, workspace_dir=self.workspace_dir)
        
        attempts = 0
        success = False
        log_content = ""

        while attempts < self.max_fix_attempts:
            result = cli.execute(prompt, self.log_cb, cwd=self.workspace_dir)
            
            out_str = (result.get('stdout') or '') + "\n" + (result.get('stderr') or '')
            if cli.check_rate_limit(out_str):
                task.status = 'WAITING_CREDITS'
                db_session.commit()
                return {"status": "waiting_credits", "message": "Rate limit hit"}
            if attempts>0:
                log_content += f"\n--------------------------\n Attempt {attempts + 1}"
            log_content += f"{result['stdout']}\n"
            
            if "STOP_FAILURE" in result['stdout']:
                success = False
                break
                
            # Compile/test validation step
            valid, test_output = self._validate_code()
            if valid:
                success = True
                break
            else:
                prompt += f"\nTests failed. Output:\n{test_output}\nPlease fix."
                log_content += f"\nTests failed:\n{test_output}\n"
                attempts += 1
                
        # Save log file
        # Naming: plan-<nomeplan>-<nomeversione>-<Commit Message>-id.md
        slug_title = self.slugify(self.plan_title)
        slug_model = self.slugify(task.model.split(':')[-1])
        slug_commit = self.slugify(task.commit_msg)
        
        filename = f"plan-{slug_title}-{slug_commit}-{task.id}.md" #{slug_model}-
        
        plan_logs_dir = os.path.join(self.logs_path, self.plan_folder or task.plan_id)
        os.makedirs(plan_logs_dir, exist_ok=True)
        log_file_path = os.path.join(plan_logs_dir, filename)
        
        with open(log_file_path, "w") as f:
            f.write(log_content)
            
        # Update Task status
        task.status = 'COMPLETED' if success else 'FAILED'
        db_session.commit()
        
        return {"status": task.status, "log_file": log_file_path}

    def _validate_code(self):
        # Placeholder for actual git/compile checks. Assuming valid for now.
        return True, "Success"
