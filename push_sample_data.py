import os
from database.models import init_db, SessionLocal, InvoiceRecord
from core.reconciler import ReconciliationEngine
from dotenv import load_dotenv

def push_sample():
    # 1. Load configuration
    load_dotenv()
    
    print("Initializing TaxPilot Database Connection...")
    try:
        init_db()
        db = SessionLocal()
        reconciler = ReconciliationEngine()
    except Exception as e:
        print(f"Connection Error: {e}")
        print("\nTIP: Make sure you replaced [YOUR-PASSWORD] in the .env file with your actual Supabase password.")
        return

    # 2. Define Sample Data (A high-value MSME invoice)
    sample_invoice = {
        'invoice_no': 'LA-2026-BULL-001',
        'supplier_gstin': '27ABCDE1234F1Z5', # Mock Maharashtra GSTIN
        'base_amount': 75000.0,
        'tax_rate': 18.0,
        'is_interstate': False,
        'total_amount_claimed': 88500.0 # Correct 18% calculation
    }

    print(f"Processing Sample Invoice: {sample_invoice['invoice_no']}...")
    
    # 3. Process through the logic engine
    result = reconciler.process_invoice(sample_invoice)
    
    # 4. Save to Cloud Database
    try:
        new_record = InvoiceRecord(
            invoice_no=sample_invoice['invoice_no'],
            supplier_gstin=sample_invoice['supplier_gstin'],
            base_amount=sample_invoice['base_amount'],
            tax_rate=sample_invoice['tax_rate'],
            total_amount_claimed=sample_invoice['total_amount_claimed'],
            status=result['status'],
            flags=result['flags']
        )
        db.add(new_record)
        db.commit()
        print(f"\nSUCCESS! Invoice successfully pushed to Supabase.")
        print(f"   Record ID: {new_record.id}")
        print(f"   Status: {result['status']}")
    except Exception as e:
        db.rollback()
        print(f"Failed to save to database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    push_sample()
