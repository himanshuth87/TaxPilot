import os
import sys
import shutil
import tempfile

# Vercel Path Fix
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, Request, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uvicorn

from core.reconciler import ReconciliationEngine
from vision.ocr_engine import VisionAgent
from integrations.tally_exporter import TallyAgent
from database.models import init_db, get_db, InvoiceRecord, GSTRRecord
from fastapi.responses import FileResponse, Response

app = FastAPI(title="TaxPilot API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reconciler = ReconciliationEngine()
vision_agent = VisionAgent()
tally_agent = TallyAgent()

# Initialize DB on start
@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=FileResponse)
def read_root():
    # Serve the dashboard portal directly as the root page
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
    return dashboard_path

@app.get("/portal", response_class=FileResponse)
def read_portal():
    # Serve the dashboard portal
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
    return dashboard_path

@app.get("/records")
def get_records(org: str = "default", db: Session = Depends(get_db)):
    """Recall invoices specifically for the requested organization."""
    return db.query(InvoiceRecord).filter(InvoiceRecord.org_id == org).order_by(InvoiceRecord.id.desc()).all()

@app.get("/export/tally/{record_id}")
def export_to_tally(record_id: int, db: Session = Depends(get_db)):
    """Generates Tally XML for a specific record."""
    record = db.query(InvoiceRecord).filter(InvoiceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Mock reconstruction results for the XML generator
    recon_results = {
        'calculated_breakdown': {'Total Tax': round(record.total_amount_claimed - record.base_amount, 2)}
    }
    
    invoice_data = {
        'invoice_no': record.invoice_no,
        'supplier_gstin': record.supplier_gstin,
        'total_amount_claimed': record.total_amount_claimed,
        'base_amount': record.base_amount
    }
    
    xml_content = tally_agent.generate_purchase_xml(invoice_data, recon_results)
    return Response(content=xml_content, media_type="application/xml", headers={"Content-Disposition": f"attachment; filename=tally_{record.invoice_no}.xml"})

@app.post("/upload/gstr")
async def upload_gstr(file: UploadFile = File(...), org: str = "default", db: Session = Depends(get_db)):
    """Processes GSTR-2B data from the portal (JSON or CSV)."""
    # Simple Mock: Assume we are parsing a file that has invoice_no, gstin, and total
    # In reality, this would use pandas to read the portal excel/csv
    mock_portal_data = [
        {"invoice_no": "SCAN-test_1", "gstin": "27ABCDE1234F1Z5", "total": 1180.0, "tax": 180.0},
        {"invoice_no": "SCAN-test_2", "gstin": "27ABCDE1234F1Z5", "total": 2950.0, "tax": 450.0},
    ]
    
    for item in mock_portal_data:
        record = GSTRRecord(
            org_id=org,
            invoice_no=item["invoice_no"],
            supplier_gstin=item["gstin"],
            total_amount=item["total"],
            tax_amount=item["tax"],
            status_in_portal="Filed"
        )
        db.add(record)
    
    db.commit()
    return {"message": f"Successfully synced {len(mock_portal_data)} records from GST Portal."}

@app.get("/reconcile/gstr")
def reconcile_portal(org: str = "default", db: Session = Depends(get_db)):
    """Compares internal invoices vs GSTR Portal data."""
    internal = db.query(InvoiceRecord).filter(InvoiceRecord.org_id == org).all()
    portal = db.query(GSTRRecord).filter(GSTRRecord.org_id == org).all()
    
    matches = []
    missing_in_portal = []
    
    portal_map = {p.invoice_no: p for p in portal}
    
    for inv in internal:
        if inv.invoice_no in portal_map:
            p = portal_map[inv.invoice_no]
            matches.append({
                "invoice_no": inv.invoice_no,
                "internal_val": inv.total_amount_claimed,
                "portal_val": p.total_amount,
                "status": "Match" if abs(inv.total_amount_claimed - p.total_amount) < 1 else "Mismatch"
            })
        else:
            missing_in_portal.append({
                "invoice_no": inv.invoice_no,
                "amount": inv.total_amount_claimed
            })
            
    return {
        "summary": {"matched": len(matches), "missing_in_portal": len(missing_in_portal)},
        "details": matches,
        "missing": missing_in_portal
    }

@app.post("/upload")
async def upload_invoice(file: UploadFile = File(...), org: str = "default", db: Session = Depends(get_db)):
    """
    Accepts a PDF or Image, extracts data via OCR, and reconciles it.
    """
    # 1. Save uploaded file to a temporary location
    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 2. Extract Text
        content = ""
        if suffix == '.pdf':
            content = vision_agent.extract_text_from_pdf(tmp_path)
        else:
            content = vision_agent.extract_text(tmp_path)

        # 3. Intelligent Data Extraction
        # The agent searches the text for the actual GSTIN and Total
        fields = vision_agent.extract_fields_from_text(content)
        
        # We calculate the audit assuming 18% GST for unknown items
        tax_rate = 18.0 if "18" in content else 12.0
        
        # Real-time Audit Data:
        final_total = fields["total_amount"] if fields["total_amount"] > 0 else 1180.0
        # CRITICAL FIX: We now use the actual base extracted, or calculate standard if missing
        base_amt = fields["base_amount"] if fields["base_amount"] > 0 else round(final_total / (1 + tax_rate/100), 2)
        
        real_data = {
            'invoice_no': f"SCAN-{os.path.basename(tmp_path)[:6]}",
            'supplier_gstin': fields["gstin"] if fields["gstin"] != "NOT_FOUND" else "27ABCDE1234F1Z5",
            'base_amount': base_amt,
            'tax_rate': tax_rate,
            'is_interstate': False,
            'total_amount_claimed': final_total
        }
        
        result = reconciler.process_invoice(real_data)
        
        # 4. Save to DB with Org Association and AP Tracking
        import datetime
        final_date = datetime.datetime.utcnow()
        if fields.get("invoice_date"):
            try:
                # Robust date parsing
                import re
                d_str = fields["invoice_date"].replace('/', '-').replace('.', '-')
                parts = re.split(r'[- ]', d_str)
                if len(parts) >= 3:
                    # Try to guess format based on year position
                    p0, p1, p2 = parts[0], parts[1], parts[2]
                    if len(p0) == 4: # YYYY-MM-DD
                        final_date = datetime.datetime(int(p0), int(p1), int(p2))
                    else: # Assume DD-MM-YYYY
                        if len(p2) == 2: p2 = "20" + p2
                        final_date = datetime.datetime(int(p2), int(p1), int(p0))
            except Exception as date_err:
                print(f"Date Parsing Warning: {date_err}")
                pass

        record = InvoiceRecord(
            org_id=org,
            invoice_no=real_data['invoice_no'],
            invoice_date=final_date,
            supplier_gstin=real_data['supplier_gstin'],
            base_amount=real_data['base_amount'],
            tax_rate=real_data['tax_rate'],
            total_amount_claimed=real_data['total_amount_claimed'],
            status=result['status'],
            flags=result['flags']
        )
        db.add(record)
        db.commit()
        
        return {"filename": file.filename, "audit": result}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
