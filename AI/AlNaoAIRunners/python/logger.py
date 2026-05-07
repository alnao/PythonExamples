import logging
import os

LOGS_PATH = os.getenv('LOGS_PATH', '.AlNaoAgent/logs')
os.makedirs(LOGS_PATH, exist_ok=True)
global_log_file = os.path.join(LOGS_PATH, 'application.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(global_log_file),
        logging.StreamHandler()
    ]
)

def get_logger(name):
    return logging.getLogger(name)
