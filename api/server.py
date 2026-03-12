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
from database.models import init_db, get_db, InvoiceRecord

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

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=FileResponse)
def read_root():
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard.html")
    return dashboard_path

@app.get("/records")
def get_records(db: Session = Depends(get_db)):
    return db.query(InvoiceRecord).order_by(InvoiceRecord.id.desc()).all()

@app.post("/upload")
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
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

        # 3. Simulate Data Parsing (This is where the 'Agent' logic lives)
        # In a full v1.0, we would use an LLM (OpenAI/Gemini) to parse this content.
        # For now, we simulate finding the GST fields in the text:
        
        # DEMO LOGIC: If '18%' is in text, assume 18% GST for the demo
        tax_rate = 18.0 if "18" in content else 12.0
        
        # We simulate a reconciliation check
        mock_data = {
            'invoice_no': f"SCAN-{os.path.basename(tmp_path)[:6]}",
            'supplier_gstin': "27ABCDE1234F1Z5", # Placeholder
            'base_amount': 1000.0,
            'tax_rate': tax_rate,
            'is_interstate': False,
            'total_amount_claimed': 1180.0
        }
        
        result = reconciler.process_invoice(mock_data)
        
        # 4. Save to DB
        record = InvoiceRecord(
            invoice_no=mock_data['invoice_no'],
            supplier_gstin=mock_data['supplier_gstin'],
            base_amount=mock_data['base_amount'],
            tax_rate=mock_data['tax_rate'],
            total_amount_claimed=mock_data['total_amount_claimed'],
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
