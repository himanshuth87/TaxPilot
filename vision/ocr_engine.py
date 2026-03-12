import re
import json

class VisionAgent:
    """
    The Vision Agent extracts text from images (invoices/receipts).
    Using lazy imports to prevent startup crashes on clouds without Tesseract.
    """
    
    def __init__(self, tesseract_path=None):
        self.tesseract_installed = True
        try:
            import pytesseract
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
        except ImportError:
            self.tesseract_installed = False

    def extract_text(self, image_path):
        """Extracts raw text from an image file."""
        if not self.tesseract_installed:
            return "Error: Tesseract OCR is not installed on this environment."
        
        try:
            import pytesseract
            from PIL import Image
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            return f"Error processing image: {e}"

    def extract_text_from_pdf(self, pdf_path):
        """Converts PDF pages to images and extracts text."""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convert PDF to a list of PIL Image objects
            pages = convert_from_path(pdf_path)
            full_text = ""
            for page in pages:
                full_text += pytesseract.image_to_string(page) + "\n"
            return full_text
        except ImportError:
            return "Error: pdf2image or poppler not installed. Use images for now."
        except Exception as e:
            return f"Error processing PDF: {e}"

    def extract_text(self, image_path):
        """Extracts raw text from an image file."""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            return f"Error processing image: {e}"

    def parse_invoice(self, text):
        """
        Heuristic-based parsing for Indian Invoices.
        In a full version, this would be passed to an LLM (Sarvam/Grok).
        """
        data = {
            "invoice_no": None,
            "gstin": None,
            "total_amount": 0.0,
            "date": None
        }

        # 1. Look for GSTIN (Standard Indian Format)
        gstin_match = re.search(r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}', text)
        if gstin_match:
            data["gstin"] = gstin_match.group(0)

        # 2. Look for Invoice Number
        inv_match = re.search(r'(Inv|Invoice|Bill|Ref)\s*(No|#)?[:.\s]*([A-Z0-9/-]+)', text, re.IGNORECASE)
        if inv_match:
            data["invoice_no"] = inv_match.group(3)

        # 3. Look for Total Amount
        # Searching for patterns like "Total: 1,234.00" or "Grand Total"
        amt_match = re.search(r'(Total|Amount|Payable)[:.\s]*[^\d]*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if amt_match:
            data["total_amount"] = float(amt_match.group(2).replace(',', ''))

        return data

if __name__ == "__main__":
    # Test stub
    agent = VisionAgent()
    print("Vision Agent Initialized. Ready for OCR processing.")
