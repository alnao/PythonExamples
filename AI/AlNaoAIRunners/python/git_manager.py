import os
import subprocess

class GitManager:
    def __init__(self, repo_url: str, workspace_dir: str, log_cb):
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir
        self.log_cb = log_cb
        self.ssh_key = os.getenv('GIT_SSH_KEY_PATH')
        self.user_name = os.getenv('GIT_USER_NAME', 'AlNao Agent')
        self.user_email = os.getenv('GIT_USER_EMAIL', 'agent@alnao.com')
        
        # If using SSH key but URL is HTTPS, rewrite to SSH format
        if self.ssh_key and self.repo_url.startswith("https://github.com/"):
            self.repo_url = self.repo_url.replace("https://github.com/", "git@github.com:")

    def _get_env(self):
        env = os.environ.copy()
        if self.ssh_key:
            env['GIT_SSH_COMMAND'] = f"ssh -i {self.ssh_key} -o StrictHostKeyChecking=no"
        return env

    def _run(self, cmd):
        self.log_cb(f"EXEC CMD: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=self._get_env())
        if result.stdout: self.log_cb(f"STDOUT: {result.stdout.strip()}")
        if result.stderr: self.log_cb(f"STDERR: {result.stderr.strip()}")
        if result.returncode != 0:
            raise Exception(f"Command failed with code {result.returncode}")
        return result

    def clone_or_pull(self, branch: str):
        git_dir = os.path.join(self.workspace_dir, '.git')
        if not os.path.exists(git_dir):
            # If directory exists but no .git, remove it to allow clean clone
            if os.path.exists(self.workspace_dir):
                import shutil
                self.log_cb(f"Workspace exists but no .git. Cleaning {self.workspace_dir}...")
                shutil.rmtree(self.workspace_dir)
            
            self._run(['git', 'clone', '-b', branch, self.repo_url, self.workspace_dir])
            # Set local user config
            self._run(['git', '-C', self.workspace_dir, 'config', 'user.name', self.user_name])
            self._run(['git', '-C', self.workspace_dir, 'config', 'user.email', self.user_email])
        else:
            # Update remote URL in case it changed (e.g. HTTPS to SSH)
            self._run(['git', '-C', self.workspace_dir, 'remote', 'set-url', 'origin', self.repo_url])
            self._run(['git', '-C', self.workspace_dir, 'checkout', branch])
            self._run(['git', '-C', self.workspace_dir, 'pull', 'origin', branch])

    def commit_step(self, message: str) -> str:
        self._run(['git', '-C', self.workspace_dir, 'add', '.'])
        
        cmd = ['git', '-C', self.workspace_dir, 'commit', '-m', message]
        self.log_cb(f"EXEC CMD: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.stdout: self.log_cb(f"STDOUT: {res.stdout.strip()}")
        if res.stderr: self.log_cb(f"STDERR: {res.stderr.strip()}")
        if res.returncode != 0 and "nothing to commit" not in res.stdout and "nothing added to commit" not in res.stdout:
            raise Exception(f"Command failed with code {res.returncode}")
            
        result = self._run(['git', '-C', self.workspace_dir, 'rev-parse', 'HEAD'])
        return result.stdout.strip()

    def push(self, branch: str):
        self._run(['git', '-C', self.workspace_dir, 'push', 'origin', branch])
