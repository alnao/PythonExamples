# AlNaoAIRunners

**AlNaoAIRunners** is an advanced automation system designed to execute complex, multi-step development plans using various AI agents (Claude, Gemini, Copilot). It manages the entire lifecycle of a development task: from cloning a repository branch to executing sequential AI-driven edits, committing progress, and backing up execution logs directly into the codebase.

## 🚀 Key Features

- **Multi-Agent Orchestration**: Sequential execution of up to 15 tasks per plan.
- **Provider Flexibility**: Seamlessly switch between **Claude CLI**, **Gemini CLI**, and **Copilot CLI**.
- **Agent Personas**: 
  - **Analyst**: Focuses on requirement gathering and code analysis.
  - **Coder**: Implements functional changes.
  - **Reviewer**: Validates code quality and logic.
  - **Caveman**: Ultra-terse, high-efficiency technical communication.
- **Git Lifecycle Management**:
  - Automatic branch cloning and pulling.
  - Sequential commits per step with custom messages and plan/step IDs.
  - Automated report generation and backup into `.alNaoAgentLogs/` in the repository.
  - SSH and HTTPS support with automatic protocol conversion for credentials.
- **Web Dashboard**: 
  - Real-time plan monitoring.
  - Interactive plan creation and cloning.
  - Integrated log viewer for worker and agent activity.
- **Robust Scheduling**: Integrated `APScheduler` for background plan execution at specific UTC times.

## 🛠️ Tech Stack

- **Backend**: Python (Flask)
- **Database**: SQLite (SQLAlchemy ORM)
- **Scheduling**: APScheduler
- **AI Integration**: Subprocess wrappers for `claude`, `gemini`, and `copilot` CLIs.
- **UI**: HTML5, Vanilla CSS, Bootstrap 5.

## ⚙️ Configuration (.env)

Customize the system behavior using the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REPO_URL` | Target Git repository URL | Required |
| `REPO_BRANCH` | Default branch for new plans | `main` |
| `BASE_WORKSPACE_DIR` | Root directory for repo clones | `/mnt/Dati4/todel/` |
| `REPO_WORKSPACE_DIR_NAME` | Subfolder name for the repo clone | `workspace` |
| `REPO_AGENT_LOGS_DIR` | Folder name for log backups in repo | `.alNaoAgentLogs` |
| `GIT_SSH_KEY_PATH` | Path to private SSH key for auth | Optional |
| `GIT_USER_NAME` | Git commit author name | `AlNao Agent` |
| `GIT_USER_EMAIL` | Git commit author email | `agent@alnao.com` |

## 📖 How it Works

1. **Plan Creation**: Define a plan via the Web UI, specifying the branch, schedule, and steps.
2. **Execution**: The worker picks up the plan at the scheduled time.
3. **Setup**: The repository is cloned into the configured workspace.
4. **Iterative Steps**:
   - The agent (Claude/Gemini/Copilot) receives the task prompt + context of all previous logs.
   - The agent performs the edit.
   - The runner commits the change with a concatenated message: `Prefix: StepMsg (Plan: ID, Step: N)`.
5. **Completion**: Execution logs (`.md` and `worker.log`) are copied into the repository, committed as a "report", and pushed to the remote branch.

## 📦 Installation

```bash
# Clone the runner
cd AlNaoAIRunners

# Install dependencies
pip install Flask python-dotenv APScheduler sqlalchemy

# Seed the DB (optional)
python seed_db.py

# Run the application
python app.py
```

*Note: Ensure the required AI CLIs (`claude`, `gemini`, `copilot`) are installed and authenticated in your environment.*





# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

