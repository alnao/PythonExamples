from datetime import datetime
import os
import subprocess
from python.providers.cli_provider_factory import CLIProviderFactory
from python.agent_builder import AgentContextBuilder
from python.database import Plan, Task, Log, db_session
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
        self.log_cb(f"-------------------------------------------------------------------------- NEW TASK: {task_id}")
        task = db_session.query(Task).get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return {"status": "error", "message": "Task not found"}
        
        plan_id = task.plan_id
        plan = db_session.query(Plan).get(plan_id)
        cli = CLIProviderFactory.get_provider(task.model)
        
        # Build initial prompt with optional common message
        task_prompt = task.prompt
        if plan and plan.common_message:
            task_prompt = f"{task_prompt}\n\n{plan.common_message}"
            
        agent_logs_dir_name = os.getenv('REPO_AGENT_LOGS_DIR', '.alNaoAgentLogs')
        work_logs_dir = os.path.join(self.workspace_dir, agent_logs_dir_name, self.plan_folder or plan_id)
        prompt = self.builder.build_prompt(plan_id, task.agent, task_prompt, workspace_dir=self.workspace_dir, work_logs_dir=work_logs_dir)
        
        attempts = 0
        success = False
        log_content = ""
        
        waiting_retries = 0
        max_waiting_retries = int(os.getenv('WAITING_CREDITS_MAX_RETRIES', '10'))
        waiting_delay_base_minutes = int(os.getenv('WAITING_CREDITS_DELAY_MINUTES', '5'))

        while attempts < self.max_fix_attempts:
            result = cli.execute(prompt, self.log_cb, cwd=self.workspace_dir)
            self.log_cb(f"Result: {result}")
            
            out_str = (result.get('stdout') or '') + "\n" + (result.get('stderr') or '')
            if cli.check_rate_limit(out_str):
                self.log_cb(f"--------------------------------------------------------------------------")
                self.log_cb(f"RATE LIMIT HIT")
                self.log_cb("OUT: \n" + out_str)
                self.log_cb("ERR: \n" + result.get('stderr') or 'NO_ERROR') 
                self.log_cb(f"--------------------------------------------------------------------------")
                log_content += f"\n[RATE LIMIT HIT]\n"

                self.log_cb("Rate limit hit. Checking retry policy...")
                if waiting_retries < max_waiting_retries:
                    waiting_retries += 1
                    current_delay = waiting_delay_base_minutes * waiting_retries
                    self.log_cb(f"Waiting {current_delay} minutes before retrying (Attempt {waiting_retries}/{max_waiting_retries})...")
                    import time
                    time.sleep(current_delay * 60)
                    continue
                else:
                    task.status = 'WAITING_CREDITS'
                    self.log_cb("Max waiting retries reached. Exiting task with WAITING_CREDITS status.")
                    break
                    
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
                
        # Update Task status
        if task.status != 'WAITING_CREDITS':
            task.status = 'COMPLETED' if success else 'FAILED'

        # Save log file
        slug_title = self.slugify(self.plan_title)
        slug_model = self.slugify(task.model.split(':')[-1])
        slug_commit = self.slugify(task.commit_msg)
        
        #filename = f"plan-{slug_title}-{slug_commit}-{task.id}.md"
        filename = f"task{task_id}-{slug_commit}-{slug_model}.md"
        plan_logs_dir = os.path.join(self.logs_path, self.plan_folder or task.plan_id)
        os.makedirs(plan_logs_dir, exist_ok=True)
        log_file_path = os.path.join(plan_logs_dir, filename)
        with open(log_file_path, "w") as f:
            f.write(f"# Task {task.step_order} of plan {self.plan_title}\n")
            f.write(f"Model: {task.model} - Agent: {task.agent}\n")
            f.write(f"Commit message: {task.commit_msg}\n\n\n")
            f.write(f"Prompt:\n{prompt}\n\n\n")
            f.write(f"Log content:\n{log_content}\n\n\n")
            f.write(f"Status: {task.status}\n")

        # create a md copy to save in the repo
        agent_logs_dir_name = os.getenv('REPO_AGENT_LOGS_DIR', '.alNaoAgentLogs')
        work_logs_dir = os.path.join(self.workspace_dir,agent_logs_dir_name, self.plan_folder)
        log_file_path_md = os.path.join(work_logs_dir, f"task{task.step_order}-{slug_commit}.md")
        os.makedirs(work_logs_dir, exist_ok=True)
        with open(log_file_path_md, "w") as f:
            f.write(f"# Task {task.step_order} of plan {self.plan_title}\n")
            f.write(f"AlNaoAIRunner runned this on {datetime.now().strftime("%d/%m/%Y %H:%M:%S") }\n")
            f.write(f"Model: {task.model} - Agent: {task.agent}\n")
            f.write(f"Commit message: {task.commit_msg}\n\n\n")
            f.write(f"Prompt:\n{prompt}\n\n\n")
            f.write(f"Log content:\n{log_content}\n\n\n")
            f.write(f"Status: {task.status}\n")

        db_session.commit()
        
        return {"status": task.status, "log_file": log_file_path}

    def _validate_code(self):
        # Placeholder for actual git/compile checks. Assuming valid for now.
        return True, "Success"
