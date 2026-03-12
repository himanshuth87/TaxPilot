from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL will come from Supabase (Free Tier)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./taxpilot_local.db")

# 🛠️ Fix for SQLAlchemy/psycopg2: strip 'pgbouncer' and other query params that cause DSN errors
if "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

# Ensure the URL is in a format SQLAlchemy likes (postgress -> postgresql)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DATABASE_URL)
    # Test connection
    with engine.connect() as conn:
        pass
except Exception as e:
    # On Vercel, the root is read-only. We must use /tmp for SQLite fallback.
    sqlite_path = "/tmp/taxpilot_local.db" if os.environ.get("VERCEL") else "./taxpilot_local.db"
    print(f"Warning: Cloud DB connection failed ({e}). Falling back to SQLite at {sqlite_path}")
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InvoiceRecord(Base):
    """
    Schema for storing every invoice processed by LedgerAgent.
    Essential for audit trails and cash-flow forecasting.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, index=True)
    supplier_gstin = Column(String)
    base_amount = Column(Float)
    tax_rate = Column(Float)
    total_amount_claimed = Column(Float)
    status = Column(String) # PASSED or FLAGGED
    flags = Column(JSON) # List of audit flags
    is_reconciled = Column(Boolean, default=False)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
