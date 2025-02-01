import pdfplumber
import re
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class GeneralBankStatementParser:
    """
    A general-purpose bank statement parser that handles various formats by:
     - Finding transaction boundaries using multiple methods
     - Detecting columns dynamically
     - Supporting multiple date formats
     - Handling various balance presentation formats
     - Based on the commonwealth parser 
    """
    
    def __init__(self):
        # Core configuration
        self.LINE_TOLERANCE = 2.0  # Vertical tolerance for grouping text
        self.COLUMN_BUFFER = 6.0   # Horizontal tolerance for column detection
        self.TRANSACTION_BUFFER = 60.0  # Buffer for transaction text grouping
        
        # Common headers to look for (case-insensitive)
        self.HEADER_VARIANTS = {
            'date': {'date', 'transaction date', 'value date', 'posting date'},
            'description': {'description', 'particulars', 'transaction', 'details', 'narrative'},
            'debit': {'debit', 'withdrawal', 'payments', 'out'},
            'credit': {'credit', 'deposit', 'deposits', 'in'}
        }
        
        # Date patterns to try (ordered by preference)
        self.DATE_PATTERNS = [
            (r'(\d{1,2})[-\s/]([A-Za-z]{3,})[-\s/](\d{2,4})', '%d %B %Y'),  # 01 January 2023
            (r'(\d{1,2})[-\s/](\d{1,2})[-\s/](\d{2,4})', '%d/%m/%Y'),      # 01/01/2023
            (r'([A-Za-z]{3,})[-\s/](\d{1,2})[-\s/](\d{2,4})', '%B %d %Y')  # January 01 2023
        ]
        
        # Balance-related keywords
        self.BALANCE_KEYWORDS = {
            'opening': {'opening balance', 'beginning balance', 'start balance'},
            'closing': {'closing balance', 'ending balance', 'final balance'}
        }

    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse various date formats into ISO format."""
        date_string = date_string.strip()
        
        for pattern, date_format in self.DATE_PATTERNS:
            match = re.search(pattern, date_string, re.IGNORECASE)
            if match:
                try:
                    # Handle 2-digit years
                    date_parts = list(match.groups())
                    if len(date_parts[-1]) == 2:
                        date_parts[-1] = '20' + date_parts[-1]
                    
                    date_str = ' '.join(date_parts)
                    parsed_date = datetime.strptime(date_str, date_format)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None

    def sanitize_amount(self, amount_str: str) -> Optional[Decimal]:
        """Clean and parse amount strings."""
        if not amount_str:
            return None
            
        # Remove currency symbols and spaces
        clean_str = amount_str.replace('$', '').replace(',', '').replace(' ', '')
        
        # Handle negative amounts in various formats
        if clean_str.endswith('-'):
            clean_str = '-' + clean_str[:-1]
        elif clean_str.endswith('DR'):
            clean_str = '-' + clean_str[:-2]
        elif clean_str.endswith('CR'):
            clean_str = clean_str[:-2]
            
        try:
            return Decimal(clean_str)
        except:
            return None

    def group_words_by_line(self, words: List[Dict], tolerance: float) -> List[List[Dict]]:
        """Group words into lines based on vertical positioning."""
        lines = []
        for word in words:
            y_pos = word["top"]
            placed = False
            
            for line in lines:
                avg_y = sum(w["top"] for w in line) / len(line)
                if abs(y_pos - avg_y) <= tolerance:
                    line.append(word)
                    placed = True
                    break
                    
            if not placed:
                lines.append([word])

        # Sort words within lines by x-position
        for line in lines:
            line.sort(key=lambda w: w["x0"])
            
        # Sort lines by y-position
        lines.sort(key=lambda ln: ln[0]["top"])
        return lines

    def detect_columns(self, lines: List[List[Dict]]) -> Dict[str, Tuple[float, float]]:
        """
        Detect column positions by finding header rows and matching against known variants.
        Returns a map of standardized column names to (x0, x1) positions.
        """
        def match_header(text: str) -> Optional[str]:
            text = text.lower().strip()
            for std_name, variants in self.HEADER_VARIANTS.items():
                if text in variants or any(v in text for v in variants):
                    return std_name
            return None

        for line in lines:
            potential_headers = {}
            for word in line:
                header_type = match_header(word["text"])
                if header_type:
                    potential_headers[header_type] = (word["x0"], word["x1"])
                    
            # Check if we found enough headers
            required_types = {'date', 'description'}
            if required_types.issubset(potential_headers.keys()):
                return potential_headers
                
        return {}

    def find_balance_boundaries(self, lines: List[List[Dict]]) -> Tuple[Optional[float], Optional[float], Optional[Decimal], Optional[Decimal]]:
        """
        Find opening and closing balances and their positions in the document.
        Returns (opening_y, closing_y, opening_amount, closing_amount).
        """
        opening_y = closing_y = None
        opening_amount = closing_amount = None
        
        for line in lines:
            text = ' '.join(w["text"] for w in line).lower()
            
            # Look for opening balance
            if not opening_y:
                for keyword in self.BALANCE_KEYWORDS['opening']:
                    if keyword in text:
                        # Extract amount using regex
                        amount_match = re.search(r'[-$,\d.]+(?:CR|DR)?', text)
                        if amount_match:
                            amt = self.sanitize_amount(amount_match.group())
                            if amt is not None:
                                opening_y = line[0]["top"]
                                opening_amount = amt
                                break
                                
            # Look for closing balance
            if not closing_y:
                for keyword in self.BALANCE_KEYWORDS['closing']:
                    if keyword in text:
                        amount_match = re.search(r'[-$,\d.]+(?:CR|DR)?', text)
                        if amount_match:
                            amt = self.sanitize_amount(amount_match.group())
                            if amt is not None:
                                closing_y = line[0]["top"]
                                closing_amount = amt
                                break

        return opening_y, closing_y, opening_amount, closing_amount

    def extract_transactions(self, lines: List[List[Dict]], columns: Dict[str, Tuple[float, float]], 
                           start_y: Optional[float], end_y: Optional[float]) -> List[Dict]:
        """Extract transactions from the document using detected columns and boundaries."""
        transactions = []
        current_transaction = None
        
        def in_column(x: float, col_name: str) -> bool:
            if col_name not in columns:
                return False
            col = columns[col_name]
            return (col[0] - self.COLUMN_BUFFER) <= x <= (col[1] + self.COLUMN_BUFFER)
        
        for line in lines:
            # Skip if outside boundaries
            if (start_y and line[0]["top"] < start_y) or (end_y and line[0]["top"] > end_y):
                continue
                
            line_text = ""
            date_str = ""
            amounts = []
            
            # Collect text and look for date and amounts
            for word in line:
                x_mid = (word["x0"] + word["x1"]) / 2
                text = word["text"].strip()
                
                if in_column("date", x_mid):
                    if self.parse_date(text):
                        date_str = text
                elif in_column("description", x_mid):
                    line_text += text + " "
                elif in_column("debit", x_mid):
                    amt = self.sanitize_amount(text)
                    if amt:
                        amounts.append(-abs(amt))  # Make debit negative
                elif in_column("credit", x_mid):
                    amt = self.sanitize_amount(text)
                    if amt:
                        amounts.append(abs(amt))   # Make credit positive
                        
            line_text = line_text.strip()
            
            # Start new transaction if we found a date
            if date_str:
                if current_transaction:
                    transactions.append(current_transaction)
                current_transaction = {
                    'date': self.parse_date(date_str),
                    'description': line_text,
                    'amount': amounts[0] if amounts else None
                }
            # Otherwise append to current transaction description
            elif current_transaction and line_text:
                current_transaction['description'] += " " + line_text
                
        # Add final transaction
        if current_transaction:
            transactions.append(current_transaction)
            
        return [t for t in transactions if t['amount'] is not None]

    def parse_statement(self, pdf_path: str) -> Dict:
        """Main entry point: Parse a bank statement PDF."""
        result = {
            'statement_info': {
                'opening_balance': None,
                'closing_balance': None,
                'total_debit': None,
                'total_credit': None
            },
            'transactions': []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Process each page
                all_lines = []
                for page in pdf.pages:
                    words = page.extract_words()
                    lines = self.group_words_by_line(words, self.LINE_TOLERANCE)
                    all_lines.extend(lines)
                    
                # Find column structure
                columns = self.detect_columns(all_lines)
                if not columns:
                    raise ValueError("Could not detect column structure")
                    
                # Find balance boundaries and amounts
                start_y, end_y, opening_bal, closing_bal = self.find_balance_boundaries(all_lines)
                if opening_bal is not None:
                    result['statement_info']['opening_balance'] = float(opening_bal)
                if closing_bal is not None:
                    result['statement_info']['closing_balance'] = float(closing_bal)
                    
                # Extract transactions
                transactions = self.extract_transactions(all_lines, columns, start_y, end_y)
                result['transactions'] = [{
                    'date': t['date'],
                    'description': t['description'],
                    'amount': float(t['amount'])
                } for t in transactions]
                
                # Calculate totals
                if transactions:
                    debits = sum(float(t['amount']) for t in transactions if float(t['amount']) < 0)
                    credits = sum(float(t['amount']) for t in transactions if float(t['amount']) > 0)
                    result['statement_info']['total_debit'] = str(abs(debits))
                    result['statement_info']['total_credit'] = str(credits)
                
        except Exception as e:
            print(f"Error parsing statement: {str(e)}")
            return result
            
        return result

def parse_unknown_statement(pdf_path: str) -> Dict:
    """Wrapper function to match the interface of other parsers."""
    parser = GeneralBankStatementParser()
    return parser.parse_statement(pdf_path)