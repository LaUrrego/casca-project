import pdfplumber
import re
import json
from combined_check_transaction_parser import process_document

def parse_us_bank_statement(pdf_path):
    def clean_amount(amt_str):
        # Handle currency formatting and negatives
        amt_str = amt_str.replace(',', '').replace('$', '').strip()
        if amt_str.endswith('-'):
            return -float(amt_str[:-1])
        return float(amt_str)

    def get_statement_details(text):
        """Extract opening and closing balances from the statement."""
        opening_balance = None
        closing_balance = None
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract opening balance
            if not opening_balance and 'Beginning Balance' in line:
                parts = re.split(r'\s{2,}', line)
                for part in parts:
                    if 'Beginning Balance' in part:
                        opening_balance = float(re.sub(r'[^\d.]', '', part.split()[-1]))

            # Extract closing balance
            if not closing_balance and 'Ending Balance' in line:
                parts = re.split(r'\s{2,}', line)
                for part in parts:
                    if 'Ending Balance' in part:
                        closing_balance = float(re.sub(r'[^\d.]', '', part.split()[-1]))

            # Stop early if both balances are found
            if opening_balance is not None and closing_balance is not None:
                break

        return opening_balance, closing_balance

    transactions = []
    opening_balance = None
    closing_balance = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Extract statement details (opening and closing balances)
            if opening_balance is None or closing_balance is None:
                ob, cb = get_statement_details(text)
                if opening_balance is None:
                    opening_balance = ob
                if closing_balance is None:
                    closing_balance = cb

            # Parse transactions
            current_section = None
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Section detection
                if 'Other Deposits' in line:
                    current_section = 'deposit'
                    continue
                elif 'Card Withdrawals' in line:
                    current_section = 'card'
                    continue
                elif 'Other Withdrawals' in line:
                    current_section = 'withdrawal'
                    continue
                elif 'Checks Paid' in line:
                    current_section = None
                
                if not current_section or any(x in line for x in ['Page', 'Member FDIC', 'usbank.com']):
                    continue

                # date detection
                date_match = re.match(r'^(Oct \d{1,2})', line)
                if date_match:
                    date = date_match.group(1)
                    amount = None
                    description = []
                    
                    # Find amount using currency pattern
                    amount_match = re.search(r'\$?\s*([\d,.]+-?)\s*$', line)
                    if amount_match:
                        amount_str = amount_match.group(1)
                        try:
                            amount = clean_amount(amount_str)
                            # Extract description before amount
                            desc_part = line[:amount_match.start()].strip()
                            description.append(desc_part)
                        except:
                            amount = None
                    
                    # Handle multi-line descriptions
                    if amount is None:
                        continue
                        
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if re.match(r'^Oct \d+', next_line) or any(x in next_line for x in ['$', 'Page']):
                            break
                        description.append(next_line)
                        j += 1
                    
                    # Clean up description
                    clean_desc = ' '.join(description)
                    # Remove extra spaces
                    clean_desc = re.sub(r'\s{2,}', ' ', clean_desc)  
                    # Remove REF numbers
                    clean_desc = re.sub(r'\bREF=.*?\b', '', clean_desc)  
                    # Remove long numbers
                    clean_desc = re.sub(r'\d{10,}', '', clean_desc)  
                    clean_desc = clean_desc.strip()
                    
                    transactions.append({
                        'date': date,
                        'description': clean_desc,
                        'amount': amount
                    })

    return {
        'statement_info': {
            'opening_balance': opening_balance,
            'closing_balance': closing_balance
        },
        'transactions': transactions
    }