import os
import sys
from core.reconciler import ReconciliationEngine
from vision.ocr_engine import VisionAgent
from integrations.tally_exporter import TallyAgent

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_cli_mode():
    reconciler = ReconciliationEngine()
    tally = TallyAgent()
    while True:
        clear_screen()
        print("--- LedgerAgent CLI Mode ---")
        inv_no = input("Invoice Number: ")
        gstin = input("Supplier GSTIN: ")
        amt = float(input("Base Amount (₹): "))
        rate = float(input("GST Rate (%): "))
        is_inter = input("Is Interstate (IGST)? (y/n): ").lower() == 'y'
        total_claimed = float(input("Total Amount on Invoice (₹): "))
        
        data = {
            'invoice_no': inv_no, 'supplier_gstin': gstin, 'base_amount': amt,
            'tax_rate': rate, 'is_interstate': is_inter, 'total_amount_claimed': total_claimed
        }
        result = reconciler.process_invoice(data)
        
        print(f"\nStatus: {result['status']}")
        for flag in result.get('flags', []): print(f"  - {flag}")
        
        if input("\nGenerate Tally XML? (y/n): ").lower() == 'y':
            xml = tally.generate_purchase_xml(data, result)
            filename = f"tally_{inv_no}.xml"
            tally.save_xml(xml, filename)
            print(f"✅ Exported to {filename}")

        if input("\nProcess another? (y/n): ").lower() != 'y': break

def main():
    while True:
        clear_screen()
        print("🚀 TAXPILOT v0.1 - SYSTEM HUB")
        print("1. CLI Reconciliation (Manual)")
        print("2. Vision Agent (OCR Image)")
        print("3. Start API Server (FastAPI)")
        print("4. Exit")
        choice = input("\nSelect Mode: ")

        if choice == '1':
            run_cli_mode()
        elif choice == '2':
            print("\nVision Agent requires an image path.")
            path = input("Image Path: ")
            agent = VisionAgent()
            text = agent.extract_text(path)
            print("\nRaw Text Found:\n", text)
            print("\nParsed Data:", agent.parse_invoice(text))
            input("\nPress Enter to return...")
        elif choice == '3':
            print("\nStarting server on http://localhost:8000")
            print("Run 'uvicorn api.server:app --reload' from terminal.")
            input("Press Enter to return...")
        elif choice == '4':
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
