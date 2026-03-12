from utils.gst_utils import validate_gstin, calculate_gst

class ReconciliationEngine:
    """
    The heart of LedgerAgent. Reconciles raw invoice data 
    against calculated tax rules and (eventually) GSTR data.
    """
    
    def __init__(self):
        self.reconciliation_log = []

    def process_invoice(self, invoice_data):
        """
        invoice_data: {
            'invoice_no': str,
            'supplier_gstin': str,
            'base_amount': float,
            'tax_rate': float,
            'is_interstate': bool,
            'total_amount_claimed': float
        }
        """
        results = {
            'invoice_no': invoice_data['invoice_no'],
            'flags': [],
            'status': 'PASSED'
        }

        # 1. Validate GSTIN
        is_valid, msg = validate_gstin(invoice_data['supplier_gstin'])
        if not is_valid:
            results['flags'].append(f"GSTIN Error: {msg}")
            results['status'] = 'FLAGGED'

        # 2. Recalculate Tax
        calculated = calculate_gst(
            invoice_data['base_amount'], 
            invoice_data['tax_rate'], 
            invoice_data['is_interstate']
        )
        
        # 3. Check for Mismatch (The Audit Trigger)
        difference = abs(calculated['Total Amount'] - invoice_data['total_amount_claimed'])
        if difference > 1.0: # Tolerance of ₹1
            results['flags'].append(
                f"Amount Mismatch! User claimed ₹{invoice_data['total_amount_claimed']}, "
                f"but calculated total is ₹{calculated['Total Amount']}. Difference: ₹{round(difference, 2)}"
            )
            results['status'] = 'FLAGGED'

        results['calculated_breakdown'] = calculated
        return results

# Example Usage logic
if __name__ == "__main__":
    reconciler = ReconciliationEngine()
    test_invoice = {
        'invoice_no': 'INV-2026-001',
        'supplier_gstin': '27AAAAA0000A1Z5', # Mock GSTIN
        'base_amount': 10000.0,
        'tax_rate': 18.0,
        'is_interstate': False,
        'total_amount_claimed': 11800.0
    }
    print(reconciler.process_invoice(test_invoice))
