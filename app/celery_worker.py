from app.celery_app import celery_app
import app.tasks  # This imports all tasks

if __name__ == '__main__':
    celery_app.start()