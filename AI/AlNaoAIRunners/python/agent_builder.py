import os

class AgentContextBuilder:
    def __init__(self, logs_dir: str, logs_path : str, plan_folder:str , plan_title:str ):
        self.logs_dir = logs_dir
        self.logs_path = logs_path
        self.plan_folder = plan_folder
        self.plan_title = plan_title
        # Ensure base logs dir exists
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)

    def build_prompt(self, plan_id: str, agent_identity: str, user_prompt: str, workspace_dir: str = None) -> str:
        # Read context logs
        plan_logs_dir = os.path.join(self.logs_path, self.plan_folder)
        
        context_logs = ""
        context_logs_list = []
        if os.path.exists(plan_logs_dir):
            for log_file in sorted(os.listdir(plan_logs_dir)):
                if log_file.endswith(".md"):
                    rel_path = os.path.join(plan_id, log_file)
                    context_logs_list.append(rel_path)
                    with open(os.path.join(plan_logs_dir, log_file), "r") as f:
                        context_logs += f"\n--- LOG {log_file} ---\n{f.read()}"

        constraint = "Constraint: Se finisci i tentativi di fix, scrivi 'STOP_FAILURE' e non fare il commit."
        
        ctx_list_str = ""
        if context_logs_list:
            ctx_list_str = "\n - ".join([os.path.abspath(os.path.join(plan_logs_dir, p)) for p in context_logs_list])


        identity_prefix = ""
        if agent_identity.lower() == "caveman":
            identity_prefix = "\nPersona: Respond terse like smart caveman. All technical substance stay. Only fluff die. Drop articles, filler, pleasantries. Short synonyms. Pattern: [thing] [action] [reason]. [next step].\n"

        full_prompt = f"""Header: {agent_identity}
{identity_prefix}
Context: Leggi lo stato attuale per sapere cosa hanno fatto i predecessori dai files.
{ctx_list_str}


{constraint}

Task: {user_prompt}
"""
        return full_prompt
