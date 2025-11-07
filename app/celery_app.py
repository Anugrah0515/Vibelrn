from celery import Celery

celery_app = Celery(
    "worker",
    broker="redis://localhost:6379/0",      # message broker
    backend="redis://localhost:6379/0"      # result storage
)
