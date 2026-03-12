import random
from database.models import init_db, SessionLocal, InvoiceRecord
from core.reconciler import ReconciliationEngine
from datetime import datetime, timedelta

def generate_demo():
    print("🚀 Generating Premium Demo Data for TaxPilot Dashboard...")
    init_db()
    db = SessionLocal()
    reconciler = ReconciliationEngine()

    vendors = [
        {"gstin": "27ABCDE1234F1Z5", "name": "Reliable Steel Corp"},
        {"gstin": "27GHIJK5678L1Z9", "name": "Modern Logistics Ltd"},
        {"gstin": "27MNOPQ9012R1Z1", "name": "Quick Office Supplies"},
        {"gstin": "27STUVW3456X1Z3", "name": "Bharat Energy"},
        {"gstin": "27YZABC7890D1Z7", "name": "Industrial Gears & Tools"}
    ]

    # Create 15 sample invoices
    for i in range(1, 16):
        vendor = random.choice(vendors)
        base = random.randint(5000, 250000)
        rate = 18.0
        
        # Introduce some "errors" for the agent to catch
        is_error = random.random() < 0.3 # 30% chance of a flag
        claimed_total = (base * 1.18)
        
        if is_error:
            # Shift the total by a few hundred rupees to simulate an error
            claimed_total += random.choice([-500.0, 450.0, -1200.0])
            inv_no = f"TP-ERR-{100 + i}"
        else:
            inv_no = f"TP-OK-{200 + i}"

        data = {
            'invoice_no': inv_no,
            'supplier_gstin': vendor['gstin'],
            'base_amount': float(base),
            'tax_rate': rate,
            'is_interstate': False,
            'total_amount_claimed': float(claimed_total)
        }

        result = reconciler.process_invoice(data)
        
        record = InvoiceRecord(
            invoice_no=inv_no,
            supplier_gstin=vendor['gstin'],
            base_amount=float(base),
            tax_rate=rate,
            total_amount_claimed=float(claimed_total),
            status=result['status'],
            flags=result['flags'],
            processed_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        
        db.add(record)
        print(f"   [{result['status']}] Created {inv_no} for ₹{claimed_total:,.2f}")

    db.commit()
    db.close()
    print("\n✅ Demo Data Generated! Open dashboard.html and refresh to see it.")

if __name__ == "__main__":
    generate_demo()
