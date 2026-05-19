AWS Polly - FastAPI + Bootstrap 5 example

Run:
1) Install dependencies:
   pip install -r requirements.txt
2) Start app:
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
3) Open:
   http://127.0.0.1:8000/

Notes:
- The app uses AWS credentials/profile available in your environment.
- By default it uses profile `default`; override with AWS_PROFILE env var.
