from app.celery_app import celery_app
import time

@celery_app.task
def send_email_task(email: str):
    print(f"Starting to send email to {email}...")
    time.sleep(5)  # simulate slow process
    print(f"Email sent successfully to {email}")
    return f"Email sent to {email}"
