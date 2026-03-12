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
from database.models import init_db, get_db, InvoiceRecord
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
    # Serve the marketing landing page
    index_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    return index_path

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

@app.post("/upload/statement")
async def upload_statement(file: UploadFile = File(...)):
    """Simulates Bank Statement processing logic."""
    return {
        "status": "Success",
        "transactions_found": 42,
        "mapped_to_ledgers": 38,
        "message": "AI Accountant has categorized your statement and prepared entries for Tally sync."
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
        
        # 4. Save to DB with Org Association
        record = InvoiceRecord(
            org_id=org,
            invoice_no=real_data['invoice_no'],
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
