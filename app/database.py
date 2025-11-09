from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, Text, ForeignKey, DateTime
)
from datetime import datetime
from sqlalchemy import inspect

# ---------------------------
# DATABASE SETUP
# ---------------------------

# Use a file-based SQLite database (persistent)
# For production, replace with PostgreSQL/MySQL URL
engine = create_engine(
    "sqlite:///./app.db",
    echo=True,
    connect_args={"check_same_thread": False}
)

# Initialize SQLAlchemy metadata
metadata_obj = MetaData()

# ---------------------------
# CATEGORY TABLE
# ---------------------------
category_table = Table(
    "category",
    metadata_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), unique=True, nullable=False),
    Column("description", Text, nullable=True),
)

# ---------------------------
# REVIEW HISTORY TABLE
# ---------------------------
review_history_table = Table(
    "review_history",
    metadata_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),  # ✅ changed to Integer for SQLite
    Column("text", Text, nullable=False),
    Column("stars", Integer, nullable=False),
    Column("review_id", String(255), nullable=False),
    Column("tone", String, nullable=True),
    Column("sentiment", String, nullable=True),
    Column("category_id", Integer, ForeignKey("category.id"), nullable=True),  # ✅ use Integer for consistency
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# ---------------------------
# ACCESS LOG TABLE
# ---------------------------
access_log_table = Table(
    "access_log",
    metadata_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),  # ✅ use Integer instead of BigInteger
    Column("text", Text, nullable=False),
)

# ---------------------------
# CREATE ALL TABLES
# ---------------------------
# Drop and recreate for clean state (optional in dev)
# metadata_obj.drop_all(engine)

metadata_obj.create_all(engine)

# ---------------------------
# VERIFY TABLES
# ---------------------------
inspector = inspect(engine)
print("Tables in database:", inspector.get_table_names())
