from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL will come from Supabase (Free Tier)
# For local testing, it defaults to a local SQLite file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ledger_agent.db")

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
