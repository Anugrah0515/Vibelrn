from fastapi import FastAPI
from app.tasks import send_email_task

app = FastAPI()

@app.get("/")
def home():
    return {"message": "FastAPI + Celery demo"}

@app.post("/send-email/")
def send_email(email: str):
    # Launch Celery task asynchronously
    send_email_task.delay(email)
    return {"message": f"Email task for {email} submitted!"}
