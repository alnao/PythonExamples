from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Plan(Base):
    __tablename__ = 'plans'
    id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    branch = Column(String, nullable=False)
    schedule_time = Column(DateTime, nullable=False)
    base_dir = Column(String, nullable=True)
    commit_prefix = Column(String, nullable=True)
    status = Column(String, default='PENDING')
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String, ForeignKey('plans.id'), nullable=False)
    step_order = Column(Integer, nullable=False)
    agent = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    commit_msg = Column(String, nullable=True)
    status = Column(String, default='PENDING')
    last_commit_hash = Column(String, nullable=True)

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    log_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(f"sqlite:///{os.getenv('DB_PATH', 'alnaoagents.db')}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db_session = Session()

def init_db(db_path):
    return db_session
