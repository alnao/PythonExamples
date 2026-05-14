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
            raise Exception(f"Command failed with code {result.returncode}: {result.stderr.strip()}")
        return result

    def _run_soft(self, cmd):
        """Run a command, return result without raising on failure."""
        self.log_cb(f"EXEC CMD: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=self._get_env())
        if result.stdout: self.log_cb(f"STDOUT: {result.stdout.strip()}")
        if result.stderr: self.log_cb(f"STDERR: {result.stderr.strip()}")
        return result

    def clone_or_pull(self, branch: str):
        """Clone or pull the main branch."""
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
            self._run(['git', '-C', self.workspace_dir, 'fetch', 'origin'])
            self._run(['git', '-C', self.workspace_dir, 'checkout', branch])
            self._run(['git', '-C', self.workspace_dir, 'pull', 'origin', branch])

    def setup_work_branch(self, main_branch: str, work_branch: str):
        """
        Setup the work branch from the main branch.
        - If work_branch doesn't exist: create it from main_branch.
        - If work_branch exists: sync it with main_branch.
          - If main is ahead: merge main into work branch.
          - If main is behind: reset work branch to main.
        """
        ws = self.workspace_dir

        # Fetch all remote branches
        self._run(['git', '-C', ws, 'fetch', 'origin'])

        # Check if work_branch exists on remote
        check = self._run_soft(['git', '-C', ws, 'ls-remote', '--heads', 'origin', work_branch])
        work_branch_exists_remote = work_branch in (check.stdout or '')

        if not work_branch_exists_remote:
            # Create new work branch from current main branch
            self.log_cb(f"Work branch '{work_branch}' does not exist. Creating from '{main_branch}'...")
            self._run(['git', '-C', ws, 'checkout', '-b', work_branch])
            self.log_cb(f"Work branch '{work_branch}' created.")
        else:
            # Work branch exists on remote, checkout and sync with main
            self.log_cb(f"Work branch '{work_branch}' exists. Syncing with '{main_branch}'...")
            
            # Checkout work branch
            checkout_res = self._run_soft(['git', '-C', ws, 'checkout', work_branch])
            if checkout_res.returncode != 0:
                # Maybe it's a remote-only branch, track it
                self._run(['git', '-C', ws, 'checkout', '-b', work_branch, f'origin/{work_branch}'])
            else:
                # Pull latest work branch
                self._run_soft(['git', '-C', ws, 'pull', 'origin', work_branch])

            # Compare main and work branch
            # Get the merge base
            merge_base_res = self._run_soft(['git', '-C', ws, 'merge-base', f'origin/{main_branch}', 'HEAD'])
            if merge_base_res.returncode != 0:
                self.log_cb("Cannot find merge base. Resetting work branch to main...")
                self._run(['git', '-C', ws, 'reset', '--hard', f'origin/{main_branch}'])
                return

            merge_base = merge_base_res.stdout.strip()
            main_head_res = self._run(['git', '-C', ws, 'rev-parse', f'origin/{main_branch}'])
            main_head = main_head_res.stdout.strip()
            work_head_res = self._run(['git', '-C', ws, 'rev-parse', 'HEAD'])
            work_head = work_head_res.stdout.strip()

            if main_head == work_head:
                self.log_cb("Main and work branch are already in sync.")
            elif merge_base == work_head:
                # Main is ahead of work → reset work to main
                self.log_cb(f"Main branch is ahead. Resetting work branch to main...")
                self._run(['git', '-C', ws, 'reset', '--hard', f'origin/{main_branch}'])
            elif merge_base == main_head:
                # Work is ahead of main → nothing to do, work has extra commits
                self.log_cb(f"Work branch is ahead of main. No sync needed.")
            else:
                # Diverged: merge main into work
                self.log_cb(f"Branches diverged. Merging main into work branch...")
                merge_res = self._run_soft(['git', '-C', ws, 'merge', f'origin/{main_branch}', 
                                           '-m', f'Sync: merge {main_branch} into {work_branch}'])
                if merge_res.returncode != 0:
                    self.log_cb("Merge conflict detected. Aborting merge and resetting to main...")
                    self._run_soft(['git', '-C', ws, 'merge', '--abort'])
                    self._run(['git', '-C', ws, 'reset', '--hard', f'origin/{main_branch}'])

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
