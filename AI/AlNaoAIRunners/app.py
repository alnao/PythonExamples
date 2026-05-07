import os
from flask import Flask, render_template, request, redirect, url_for
import uuid
from datetime import datetime
from dotenv import load_dotenv
from python.database import init_db, Plan, Task
from python.worker import start_worker

load_dotenv()

app = Flask(__name__)
app.config['DB_PATH'] = os.getenv('DB_PATH', 'alnaoagents.db')

# Init DB Session
db_session = init_db(app.config['DB_PATH'])
start_worker()

@app.route('/')
def index():
    plans = db_session.query(Plan).order_by(Plan.created_at.desc()).all()
    return render_template('index.html', plans=plans)

@app.route('/plan/<plan_id>')
def plan_detail(plan_id):
    plan = db_session.query(Plan).get(plan_id)
    tasks = db_session.query(Task).filter_by(plan_id=plan_id).order_by(Task.step_order).all()
    
    logs_path = os.getenv('LOGS_PATH', '.AlNaoAgent/logs')
    worker_log_path = os.path.join(logs_path, plan_id, 'worker.log')
    worker_log = ""
    if os.path.exists(worker_log_path):
        try:
            with open(worker_log_path, 'r') as f:
                worker_log = f.read()
        except:
            worker_log = "Error reading log file."
            
    return render_template('plan.html', plan=plan, tasks=tasks, worker_log=worker_log)

@app.route('/plan/new', methods=['GET', 'POST'])
def create_plan():
    if request.method == 'POST':
        title = request.form.get('title')
        branch = request.form.get('branch')
        base_dir = request.form.get('base_dir')
        commit_prefix = request.form.get('commit_prefix')
        sched_str = request.form.get('schedule_time')
        try:
            schedule_time = datetime.fromisoformat(sched_str) if sched_str else datetime.utcnow()
        except:
            schedule_time = datetime.utcnow()
            
        plan_id = f"plan-{str(uuid.uuid4())[:8]}"
        plan = Plan(id=plan_id, title=title, branch=branch, schedule_time=schedule_time, 
                    base_dir=base_dir, commit_prefix=commit_prefix, status='PENDING')
        db_session.add(plan)
        
        step_counter = 1
        for i in range(1, 16):
            prompt = request.form.get(f'prompt_{i}', '').strip()
            if prompt:
                agent = request.form.get(f'agent_{i}', 'DefaultAgent')
                if not agent: agent = 'DefaultAgent'
                model = request.form.get(f'model_{i}', 'claude')
                commit_msg = request.form.get(f'commit_msg_{i}', '')
                task = Task(plan_id=plan_id, step_order=step_counter, agent=agent, model=model, 
                            prompt=prompt, commit_msg=commit_msg, status='PENDING')
                db_session.add(task)
                step_counter += 1
                
        db_session.commit()
        return redirect(url_for('index'))
    
    clone_from = request.args.get('clone_from')
    cloned_plan = None
    cloned_tasks = []
    if clone_from:
        cloned_plan = db_session.query(Plan).get(clone_from)
        if cloned_plan:
            cloned_tasks = db_session.query(Task).filter_by(plan_id=clone_from).order_by(Task.step_order).all()

    return render_template('create_plan.html', 
                           cloned_plan=cloned_plan, 
                           cloned_tasks=cloned_tasks, 
                           now=datetime.utcnow().strftime('%Y-%m-%dT%H:%M'),
                           default_base_dir=os.getenv('BASE_WORKSPACE_DIR', '/mnt/Dati4/todel/'),
                           default_branch=os.getenv('REPO_BRANCH', 'main'))

@app.route('/task/<int:task_id>/action', methods=['POST'])
def task_action(task_id):
    action = request.form.get('action')
    task = db_session.query(Task).get(task_id)
    if action == 'continue' and task.status == 'WAITING_CREDITS':
        task.status = 'PENDING'
        plan = db_session.query(Plan).get(task.plan_id)
        if plan.status == 'WAITING_CREDITS':
            plan.status = 'PENDING'
        db_session.commit()
    return redirect(url_for('plan_detail', plan_id=task.plan_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
