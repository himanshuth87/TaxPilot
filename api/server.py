from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.reconciler import ReconciliationEngine
from vision.ocr_engine import VisionAgent
from database.models import init_db, get_db, InvoiceRecord
from sqlalchemy.orm import Session
import uvicorn

app = FastAPI(title="TaxPilot API", version="0.1")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
reconciler = ReconciliationEngine()
vision_agent = VisionAgent()

# Initialize DB on start
@app.on_event("startup")
def startup_event():
    init_db()

class InvoiceRequest(BaseModel):
    invoice_no: str
    supplier_gstin: str
    base_amount: float
    tax_rate: float
    is_interstate: bool
    total_amount_claimed: float

@app.post("/reconcile")
def reconcile_invoice(req: InvoiceRequest, db: Session = Depends(get_db)):
    """
    Processes an invoice AND saves it to the permanent database.
    """
    try:
        # 1. Logic Processing
        result = reconciler.process_invoice(req.dict())
        
        # 2. Persist to Database
        db_record = InvoiceRecord(
            invoice_no=req.invoice_no,
            supplier_gstin=req.supplier_gstin,
            base_amount=req.base_amount,
            tax_rate=req.tax_rate,
            total_amount_claimed=req.total_amount_claimed,
            status=result['status'],
            flags=result['flags']
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        result['db_id'] = db_record.id
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/records")
def get_records(db: Session = Depends(get_db)):
    """Recall all processed invoices for your Dashboard."""
    return db.query(InvoiceRecord).all()

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Skeleton for WhatsApp Webhook.
    This will eventually receive image URLs from Twilio/Interakt.
    """
    body = await request.json()
    print(f"Received WhatsApp Webhook: {body}")
    
    # Logic: 
    # 1. Extract image URL from message
    # 2. image = download_image(url)
    # 3. text = vision_agent.extract_text(image)
    # 4. parsed_data = vision_agent.parse_invoice(text)
    # 5. response_msg = reconciler.process_invoice(parsed_data)
    # 6. send_whatsapp_reply(response_msg)
    
    return {"status": "acknowledged"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
