from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, BigInteger, Text, ForeignKey, DateTime
)
from datetime import datetime

# For production, replace with a file-based SQLite database or other database URL
engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)

# Initialize SQLAlchemy metadata
metadata_obj = MetaData()

# ---------------------------
# Category Table
# ---------------------------
category_table = Table(
    "category",
    metadata_obj,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", String(255), unique=True, nullable=False),
    Column("description", Text, nullable=True),
)

# ---------------------------
# Review History Table
# ---------------------------
review_history_table = Table(
    "review_history",
    metadata_obj,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("text", Text, nullable=False),
    Column("stars", Integer, nullable=False),
    Column("review_id", String(255), nullable=False),
    Column("tone", String, nullable=True),
    Column("sentiment", String, nullable=True),
    Column("category_id", BigInteger, ForeignKey("category.id"), nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# ---------------------------
# Access Log Table
# ---------------------------
access_log_table = Table(
    "access_log",
    metadata_obj,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("text", Text, nullable=False),
)

# Create all tables in DB
metadata_obj.create_all(engine)