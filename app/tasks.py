from app.celery_app import celery_app
import time
from datetime import datetime
from sqlalchemy import select, func, desc, and_
from app.database import (
    engine, category_table, review_history_table, access_log_table
)


@celery_app.task
def log_access_task(log_text: str):
    with engine.connect() as conn:
        ins = access_log_table.insert().values(text=log_text)
        conn.execute(ins)
        conn.commit()
    return f"Access log saved: {log_text}"


# ---- Synchronous helper implementations used by endpoints ----
def add_category_impl(name: str, description: str = None):
    """Create a category if it doesn't already exist."""
    with engine.connect() as conn:
        sel = category_table.select().where(category_table.c.name == name)
        result = conn.execute(sel).fetchone()
        if result:
            return {"message": f"Category '{name}' already exists!"}
        ins = category_table.insert().values(name=name, description=description)
        conn.execute(ins)
        conn.commit()
    return {"message": f"Category '{name}' added!"}


def list_categories_impl():
    with engine.connect() as conn:
        sel = category_table.select()
        result = conn.execute(sel).fetchall()
        return [{"id": row.id, "name": row.name, "description": row.description} for row in result]


def add_review_impl(text: str, stars: int, review_id: str, tone: str = None, sentiment: str = None, category_id: int = None):
    with engine.connect() as conn:
        ins = review_history_table.insert().values(
            text=text,
            stars=stars,
            review_id=review_id,
            tone=tone,
            sentiment=sentiment,
            category_id=category_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        conn.execute(ins)
        conn.commit()
    return {"message": "Review added!"}


def list_reviews_impl():
    with engine.connect() as conn:
        sel = review_history_table.select()
        result = conn.execute(sel).fetchall()
        return [{
            "id": row.id,
            "text": row.text,
            "stars": row.stars,
            "review_id": row.review_id,
            "tone": row.tone,
            "sentiment": row.sentiment,
            "category_id": row.category_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        } for row in result]


def get_reviews_by_category_impl(category_id: int, page_size: int = 15):
    """Return up to `page_size` most recent reviews for a category, considering only latest review_history per review_id.

    This mirrors the previous logic from `main.py` but as a reusable function.
    """
    PAGE_SIZE = page_size
    with engine.connect() as conn:
        category_query = category_table.select().where(category_table.c.id == category_id)
        category = conn.execute(category_query).fetchone()
        if not category:
            return {"error": f"Category with id {category_id} not found"}

        # Get the latest created_at timestamp for this category
        last_created_query = (
            select([func.max(review_history_table.c.created_at)])
            .where(review_history_table.c.category_id == category_id)
        )
        last_created = conn.execute(last_created_query).scalar()

        if not last_created:
            return {
                "category": {"id": category.id, "name": category.name, "description": category.description},
                "reviews": [],
                "total_reviews": 0
            }

        # Subquery to get the latest version of each review
        latest_reviews = (
            select([
                review_history_table.c.review_id,
                func.max(review_history_table.c.created_at).label('max_created_at')
            ])
            .where(review_history_table.c.category_id == category_id)
            .group_by(review_history_table.c.review_id)
            .alias('latest_reviews')
        )

        # Main query to get reviews
        query = (
            select([
                review_history_table.c.id,
                review_history_table.c.text,
                review_history_table.c.stars,
                review_history_table.c.review_id,
                review_history_table.c.created_at,
                review_history_table.c.tone,
                review_history_table.c.sentiment,
                review_history_table.c.category_id
            ])
            .select_from(
                review_history_table.join(
                    latest_reviews,
                    and_(
                        review_history_table.c.review_id == latest_reviews.c.review_id,
                        review_history_table.c.created_at == latest_reviews.c.max_created_at
                    )
                )
            )
            .where(review_history_table.c.created_at <= last_created)
            .order_by(desc(review_history_table.c.created_at))
            .limit(PAGE_SIZE)
        )

        result = conn.execute(query).fetchall()

        reviews_list = [{
            "id": row.id,
            "text": row.text,
            "stars": row.stars,
            "review_id": row.review_id,
            "created_at": row.created_at,
            "tone": row.tone,
            "sentiment": row.sentiment,
            "category_id": row.category_id
        } for row in result]

        response = {
            "category": {"id": category.id, "name": category.name, "description": category.description},
            "reviews": reviews_list,
            "total_reviews": len(reviews_list)
        }

    return response


def get_review_trends_impl(limit: int = 5):
    with engine.connect() as conn:
        # Subquery to get the latest review for each review_id
        latest_reviews = (
            select([
                review_history_table.c.review_id,
                review_history_table.c.stars,
                review_history_table.c.category_id,
                func.max(review_history_table.c.created_at).label('max_created_at')
            ])
            .group_by(review_history_table.c.review_id)
            .alias('latest_reviews')
        )

        # Main query to get category statistics
        query = (
            select([
                category_table.c.id,
                category_table.c.name,
                category_table.c.description,
                func.count(latest_reviews.c.review_id).label('total_reviews'),
                func.avg(latest_reviews.c.stars).label('average_stars')
            ])
            .select_from(
                category_table.join(
                    latest_reviews,
                    category_table.c.id == latest_reviews.c.category_id
                )
            )
            .group_by(category_table.c.id, category_table.c.name, category_table.c.description)
            .order_by(desc('average_stars'))
            .limit(limit)
        )

        result = conn.execute(query).fetchall()

        trends = [{
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "average_stars": float(row.average_stars),
            "total_reviews": row.total_reviews
        } for row in result]

    return {"trends": trends}
