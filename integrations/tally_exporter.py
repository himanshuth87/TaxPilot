from datetime import datetime

class TallyAgent:
    """
    The Tally Agent converts reconciled data into Tally-compatible XML format.
    This allows the user to import their business data into Tally Prime instantly.
    """

    def generate_purchase_xml(self, invoice_data, reconciliation_results):
        """
        Generates a basic Tally XML for a Purchase Voucher.
        """
        now = datetime.now().strftime("%Y%m%d")
        
        xml_template = f"""
<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>LedgerAgent Example Co</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="AccountingVoucher">
                        <DATE>{now}</DATE>
                        <VOUCHERNUMBER>{invoice_data['invoice_no']}</VOUCHERNUMBER>
                        <PARTYLEDGERNAME>Supplier {invoice_data['supplier_gstin']}</PARTYLEDGERNAME>
                        <PERSISTEDVIEW>AccountingVoucher</PERSISTEDVIEW>
                        
                        <!-- Credit Entry for Party -->
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Supplier {invoice_data['supplier_gstin']}</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{invoice_data['total_amount_claimed']}</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>

                        <!-- Debit Entry for Purchase Account (Base Amount) -->
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>Purchase Account</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{invoice_data['base_amount']}</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>

                        <!-- GST Entries -->
                        <ALLLEDGERENTRIES.LIST>
                            <LEDGERNAME>GST Input Tax</LEDGERNAME>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{reconciliation_results['calculated_breakdown']['Total Tax']}</AMOUNT>
                        </ALLLEDGERENTRIES.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>
"""
        return xml_template.strip()

    def save_xml(self, xml_content, filename):
        with open(filename, 'w') as f:
            f.write(xml_content)
        return filename

if __name__ == "__main__":
    agent = TallyAgent()
    print("Tally Agent Initialized. Ready to generate Tally XMLs.")
