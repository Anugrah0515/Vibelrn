from fastapi import FastAPI, Query
from app.tasks import (
    log_access_task,
    add_category_impl,
    list_categories_impl,
    add_review_impl,
    list_reviews_impl,
    get_reviews_by_category_impl,
    get_review_trends_impl,
)
from sqlalchemy import (
    func, desc, and_, select
)
from datetime import datetime
from sqlalchemy.sql import distinct
from typing import Optional
from app.database import (
    engine, category_table, review_history_table, access_log_table
)

# Initialize FastAPI app
app = FastAPI()

# ---------------------------
# FastAPI Endpoints
# ---------------------------
@app.get("/")
def home():
    # Log access asynchronously using Celery
    log_access_task.delay("GET /")
    return {"message": "FastAPI + Celery + SQLAlchemy demo"}

@app.post("/add-category/")
def add_category(name: str, description: str = None):
    # Log access asynchronously using Celery
    log_access_task.delay(f"POST /add-category/ name={name}")
    return add_category_impl(name, description)

@app.get("/categories/")
def list_categories():
    # Log access asynchronously using Celery
    log_access_task.delay("GET /categories/")
    categories = list_categories_impl()
    return {"categories": categories}

@app.post("/review/add-review/")
def add_review(text: str, stars: int, review_id: str, tone: str = None, sentiment: str = None, category_id: int = None):
    # Log access asynchronously using Celery
    log_access_task.delay(f"POST /review/add-review/ review_id={review_id}")
    return add_review_impl(text, stars, review_id, tone, sentiment, category_id)

@app.get("/reviews/")
def list_reviews():
    # Log access asynchronously using Celery
    log_access_task.delay("GET /reviews/")
    reviews = list_reviews_impl()
    return {"reviews": reviews}

@app.get("/reviews/by-category/")
def get_reviews_by_category(
    category_id: int = Query(..., description="ID of the category to fetch reviews for")
):
    # Log access asynchronously using Celery
    log_access_task.delay(f"GET /reviews/by-category/?category_id={category_id}")
    return get_reviews_by_category_impl(category_id)

@app.get("/reviews/trends")
def get_review_trends():
    # Log access asynchronously using Celery
    log_access_task.delay("GET /reviews/trends")
    return get_review_trends_impl()