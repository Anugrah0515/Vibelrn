from app.celery_app import celery_app
from datetime import datetime
from sqlalchemy import select, func, desc, and_
from app.database import engine, category_table, review_history_table, access_log_table
import os, json

# ----------------------------
# OpenAI Setup (supports both new + old SDKs)
# ----------------------------
OPENAI_AVAILABLE = False
USE_NEW_SDK = False

try:
    # Try new OpenAI SDK (>=1.x)
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
    USE_NEW_SDK = True
except Exception:
    try:
        # Fallback to legacy SDK (<1.x)
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        client = openai
        OPENAI_AVAILABLE = True
        USE_NEW_SDK = False
    except Exception:
        client = None
        OPENAI_AVAILABLE = False


# ----------------------------
# Celery Task
# ----------------------------
@celery_app.task(name="app.tasks.log_access_task")
def log_access_task(log_text: str):
    """Log access to database asynchronously."""
    with engine.begin() as conn:
        conn.execute(
            access_log_table.insert().values(
                text=log_text, created_at=datetime.utcnow()
            )
        )
    return f"Access log saved: {log_text}"


# ----------------------------
# Helper Implementations
# ----------------------------
def add_category_impl(name: str, description: str = None):
    with engine.begin() as conn:
        existing = conn.execute(
            select(category_table).where(category_table.c.name == name)
        ).fetchone()
        if existing:
            return {"message": f"Category '{name}' already exists!"}

        conn.execute(category_table.insert().values(name=name, description=description))
    return {"message": f"Category '{name}' added!"}


def list_categories_impl():
    with engine.connect() as conn:
        result = conn.execute(select(category_table)).fetchall()
        return [
            {"id": row.id, "name": row.name, "description": row.description}
            for row in result
        ]


def add_review_impl(text: str, stars: int, review_id: str, tone: str = None, sentiment: str = None, category_id: int = None):
    with engine.begin() as conn:
        conn.execute(
            review_history_table.insert().values(
                text=text,
                stars=stars,
                review_id=review_id,
                tone=tone,
                sentiment=sentiment,
                category_id=category_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
    return {"message": "Review added!"}


def list_reviews_impl():
    with engine.connect() as conn:
        result = conn.execute(select(review_history_table)).fetchall()
        return [
            {
                "id": row.id,
                "text": row.text,
                "stars": row.stars,
                "review_id": row.review_id,
                "tone": row.tone,
                "sentiment": row.sentiment,
                "category_id": row.category_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in result
        ]


# ----------------------------
# GPT Tone/Sentiment Analyzer
# ----------------------------
def analyze_tone_and_sentiment(text: str, stars: int):
    """Call OpenAI (new or old SDK) to get tone and sentiment."""
    if not OPENAI_AVAILABLE or not os.getenv("OPENAI_API_KEY"):
        return None, None

    system_prompt = (
        "You are a helpful assistant that classifies short product reviews. "
        "Return a JSON object with two keys: 'tone' and 'sentiment'."
    )
    user_prompt = f"Review text: {text}\nStars: {stars}\n\nReturn JSON only."

    try:
        if USE_NEW_SDK:
            # For openai>=1.x
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=120,
            )
            content = response.choices[0].message.content.strip()
        else:
            # For openai<1.x
            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=120,
            )
            content = response["choices"][0]["message"]["content"].strip()

        # Parse JSON safely
        try:
            parsed = json.loads(content)
        except Exception:
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(content[start:end+1])
            else:
                return None, None

        return parsed.get("tone"), parsed.get("sentiment")
    except Exception as e:
        print("⚠️ OpenAI API error:", e)
        return None, None


# ----------------------------
# Reviews by Category
# ----------------------------
def get_reviews_by_category_impl(category_id: int, page_size: int = 15):
    PAGE_SIZE = page_size

    with engine.connect() as conn:
        category = conn.execute(
            select(category_table).where(category_table.c.id == category_id)
        ).fetchone()
        if not category:
            return {"error": f"Category with id {category_id} not found"}

        last_created = conn.execute(
            select(func.max(review_history_table.c.created_at)).where(
                review_history_table.c.category_id == category_id
            )
        ).scalar()

        if not last_created:
            return {
                "category": {"id": category.id, "name": category.name, "description": category.description},
                "reviews": [],
                "total_reviews": 0,
            }

        latest_reviews = (
            select(
                review_history_table.c.review_id,
                func.max(review_history_table.c.created_at).label("max_created_at"),
            )
            .where(review_history_table.c.category_id == category_id)
            .group_by(review_history_table.c.review_id)
            .subquery("latest_reviews")
        )

        query = (
            select(
                review_history_table.c.id,
                review_history_table.c.text,
                review_history_table.c.stars,
                review_history_table.c.review_id,
                review_history_table.c.created_at,
                review_history_table.c.tone,
                review_history_table.c.sentiment,
                review_history_table.c.category_id,
            )
            .select_from(
                review_history_table.join(
                    latest_reviews,
                    and_(
                        review_history_table.c.review_id == latest_reviews.c.review_id,
                        review_history_table.c.created_at == latest_reviews.c.max_created_at,
                    ),
                )
            )
            .where(review_history_table.c.created_at <= last_created)
            .order_by(desc(review_history_table.c.created_at))
            .limit(PAGE_SIZE)
        )

        rows = conn.execute(query).fetchall()

    # Convert and enrich
    reviews_list = [
        {
            "id": r.id,
            "text": r.text,
            "stars": r.stars,
            "review_id": r.review_id,
            "created_at": r.created_at,
            "tone": r.tone,
            "sentiment": r.sentiment,
            "category_id": r.category_id,
        }
        for r in rows
    ]

    # Enrich missing tone/sentiment
    for idx, r in enumerate(reviews_list):
        if not r.get("tone") or not r.get("sentiment"):
            tone_val, sentiment_val = analyze_tone_and_sentiment(r["text"], r["stars"])
            if tone_val or sentiment_val:
                with engine.begin() as conn:
                    conn.execute(
                        review_history_table.update()
                        .where(review_history_table.c.id == r["id"])
                        .values(
                            tone=tone_val,
                            sentiment=sentiment_val,
                            updated_at=datetime.utcnow(),
                        )
                    )
                reviews_list[idx]["tone"] = tone_val
                reviews_list[idx]["sentiment"] = sentiment_val

    return {
        "category": {"id": category.id, "name": category.name, "description": category.description},
        "reviews": reviews_list,
        "total_reviews": len(reviews_list),
    }


# ----------------------------
# Review Trends
# ----------------------------
def get_review_trends_impl(limit: int = 5):
    with engine.connect() as conn:
        latest_reviews = (
            select(
                review_history_table.c.review_id,
                review_history_table.c.stars,
                review_history_table.c.category_id,
                func.max(review_history_table.c.created_at).label("max_created_at"),
            )
            .group_by(review_history_table.c.review_id)
            .subquery("latest_reviews")
        )

        query = (
            select(
                category_table.c.id,
                category_table.c.name,
                category_table.c.description,
                func.count(latest_reviews.c.review_id).label("total_reviews"),
                func.avg(latest_reviews.c.stars).label("average_stars"),
            )
            .select_from(
                category_table.join(
                    latest_reviews,
                    category_table.c.id == latest_reviews.c.category_id,
                )
            )
            .group_by(
                category_table.c.id,
                category_table.c.name,
                category_table.c.description,
            )
            .order_by(desc("average_stars"))
            .limit(limit)
        )

        result = conn.execute(query).fetchall()

    return {
        "trends": [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "average_stars": float(row.average_stars or 0.0),
                "total_reviews": row.total_reviews,
            }
            for row in result
        ]
    }
