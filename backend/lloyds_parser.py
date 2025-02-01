import pdfplumber
import re
from datetime import datetime
import json

def parse_lloyds_statement(pdf_path):
    """
    Parse a Lloyds bank statement PDF and extract transaction data.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Structured data containing statement info and transactions
    """
    
    def clean_amount(amount_str):
        if amount_str:
            return float(amount_str.replace(',', '').replace('£', '').strip())
        return 0.0
    
    def parse_date(date_str):
        """Parse date formats like '04 Sep19' or '05 Oct 19'."""
        date_match = re.match(r'(\d{2})\s+([A-Za-z]{3})\s*(\d{2})', date_str)
        if date_match:
            day, month, year_part = date_match.groups()
            year = f'20{year_part}'  # Assumes 21st century
            try:
                return datetime.strptime(f"{day} {month} {year}", '%d %b %Y').date().isoformat()
            except ValueError:
                return None
        return None
        
    def parse_three_line_statement(text):
        """
        Parses the multi-line statement:
        1) "Money In £5420.12 Balance on 01 September 2019 £1173.56"
        2) "Money Out £2062.05"
        3) "£3801.48 Balance on 30 November 2019"
        and maps them to:
        total_credit=5420.12,
        opening_balance=1173.56,
        total_debit=3801.48,   # i.e. the total debit
        closing_balance=2062.05
        HACK due to issues with document layout
        """
        
        statement_data = {
            'total_credit': None,
            'opening_balance': None,
            'total_debit': None,
            'closing_balance': None,
        }

        # Split into lines
        lines = text.strip().split('\n')

        line1_pattern = re.compile(
            r'Money\s+In\s+£([\d,]+\.\d{2})\s+Balance\s+on\s+\d{1,2}\s+\w+\s+\d{4}\s+£([\d,]+\.\d{2})'
        )
        line2_pattern = re.compile(
            r'Money\s+Out\s+£([\d,]+\.\d{2})'
        )
        line3_pattern = re.compile(
            r'£([\d,]+\.\d{2})\s+Balance\s+on\s+\d{1,2}\s+\w+\s+\d{4}'
        )

        for line in lines:
            line1_match = line1_pattern.search(line)
            if line1_match:
                statement_data['total_credit'] = float(line1_match.group(1).replace(',',''))
                statement_data['opening_balance'] = float(line1_match.group(2).replace(',',''))

            line2_match = line2_pattern.search(line)
            if line2_match:
                # This is actually the final/closing balance
                statement_data['closing_balance'] = float(line2_match.group(1).replace(',',''))

            line3_match = line3_pattern.search(line)
            if line3_match:
                # This is actually the "money out" (total debit)
                statement_data['total_debit'] = -float(line3_match.group(1).replace(',',''))

        return statement_data

    def extract_lloyds_summary(first_page):
        # Assume the summary is on page 1
        # first_page = pdf.pages[0]
            
        # Get page dimensions
        page_width = first_page.width
        page_height = first_page.height

        # Crop the top ~1/3 or 1/2 of the page 
        # pdfplumber coordinates: (x0, y0, x1, y1) from bottom-left
        # so top portion might be from y=page_height/2 to y=page_height
        top_half_bbox = (0, 0, page_width, page_height/2)
        top_half = first_page.crop(top_half_bbox)
        
        # Extract text from that top portion
        cropped_text = top_half.extract_text()


        return parse_three_line_statement(cropped_text)



    def parse_transactions(text):
        transactions = []
        lines = text.split('\n')
        
        payment_codes = {
            'BGC', 'BNS', 'BP', 'CHG', 'CHQ', 'COM', 'COR', 'CPT', 'CSH', 'CSQ',
            'DD', 'DEB', 'DEP', 'EFT', 'EUR', 'FE', 'FEE', 'FPC', 'FPI', 'FPO',
            'IB', 'INT', 'MPI', 'MPO', 'MTG', 'NS', 'NSC', 'OTH', 'PAY', 'PSB',
            'PSV', 'SAL', 'SPB', 'SO', 'STK', 'TD', 'TDG', 'TDI', 'TDN', 'TFR',
            'UT', 'SUR'
        }
        
        payment_code_type = {
            'BGC': 'Credit',
            'BNS': 'Credit',
            'BP': 'Debit',
            'CHG': 'Debit',
            'CHQ': 'Debit',
            'COM': 'Debit',
            'COR': 'Adjustment',
            'CPT': 'Debit',
            'CSH': 'Credit',
            'CSQ': 'Debit',
            'DD': 'Debit',
            'DEB': 'Debit',
            'DEP': 'Credit',
            'EFT': 'Debit',
            'EUR': 'Debit',
            'FE': 'Adjustment',
            'FEE': 'Debit',
            'FPC': 'Debit',
            'FPI': 'Credit',
            'FPO': 'Debit',
            'IB': 'Debit',
            'INT': 'Credit',
            'MPI': 'Credit',
            'MPO': 'Debit',
            'MTG': 'Debit',
            'NS': 'Credit',
            'NSC': 'Credit',
            'OTH': 'Adjustment',
            'PAY': 'Debit',
            'PSB': 'Credit',
            'PSV': 'Debit',
            'SAL': 'Credit',
            'SPB': 'Debit',
            'SO': 'Debit',
            'STK': 'Adjustment',
            'TD': 'Credit',
            'TDG': 'Credit',
            'TDI': 'Credit',
            'TDN': 'Credit',
            'TFR': 'Credit',
            'UT': 'Adjustment',
            'SUR': 'Debit'
        }
        
        for line in lines:
            line = line.strip()
            if any(skip in line for skip in ["Balance", "Date", "Lloyds Bank"]):
                continue
            
            tokens = line.split()
            if len(tokens) < 4:
                continue  # Skip invalid lines
            
            try:
                date_str = f"{tokens[0]} {tokens[1]} {tokens[2] if str(tokens[2]).isalnum() else ''}"
                date = parse_date(date_str)
            except:
                print(f"Skipping line with invalid date: {line}")
                continue
            
            # Find payment code in tokens
            payment_code = None
            code_idx = -1
            for idx, token in enumerate(tokens[2:], start=2):
                if token in payment_codes:
                    payment_code = token
                    code_idx = idx
                    break
            
            if not payment_code:
                print(f"No payment code found: {line}")
                continue
            
            # Extract description and amount
            description = ' '.join(tokens[2:code_idx])
            amount_str = tokens[code_idx + 1] if code_idx + 1 < len(tokens) else None
            amount = clean_amount(amount_str) if amount_str else 0.0
            
            # Determine credit/debit
            trans_type = payment_code_type.get(payment_code, 'Unknown')
            if trans_type == 'Credit':
                amount = abs(amount)
            elif trans_type == 'Debit':
                amount = -abs(amount)
            else:
                amount = 0.0  
            
            transactions.append({
                'date': date,
                'description': f"{description} ({payment_code})",
                'amount': amount
            })
        
        return transactions
    
    def format_output(parsed_data):
        """Format the parsed data as JSON with proper indentation"""
        return json.dumps(parsed_data, indent=2)
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages)
        first_page = pdf.pages[0]
        
        output =  {
            'statement_info': extract_lloyds_summary(first_page),
            'transactions': parse_transactions(full_text)
        }
    return format_output(output)

def format_output(parsed_data):
    """Format the parsed data as JSON with proper indentation"""
    return json.dumps(parsed_data, indent=2)