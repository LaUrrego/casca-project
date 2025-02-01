import pdfplumber
import pandas as pd
import json
from datetime import datetime
import re

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF using pdfplumber while preserving table structure
    """
    all_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract tables from the page
                tables = page.extract_tables()
                for table in tables:
                    # Filter out None and empty strings
                    filtered_rows = [
                        [cell.strip() if isinstance(cell, str) else str(cell) for cell in row if cell is not None]
                        for row in table
                        if any(cell is not None and str(cell).strip() for cell in row)
                    ]
                    all_text.extend(filtered_rows)
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    return all_text

def parse_amount(amount_str):
    """
    Parse amount string to float, handling commas and invalid values
    """
    try:
        if not amount_str or amount_str.strip() == '':
            return 0.0
        return float(amount_str.replace(',', ''))
    except (ValueError, TypeError):
        return 0.0

def parse_date(date_str):
    """
    Parse date string to YYYY-MM-DD format
    """
    try:
        date_obj = datetime.strptime(date_str, '%d-%b-%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        return None

def parse_idfc_statement(pdf_path):
    """
    Parse IDFC bank statement PDF and return JSON format of transactions
    and balance information.
    """
    # Extract text from PDF
    rows = extract_text_from_pdf(pdf_path)
    
    # Find the summary row containing opening/closing balances
    summary_row = None
    for i, row in enumerate(rows):
        if 'Opening Balance' in row:
            summary_row = dict(zip(rows[i], rows[i+1]))
            break

    if not summary_row:
        raise ValueError("Could not find balance information")
    
    # Extract balance information
    opening_balance = summary_row['Opening Balance']
    total_debit = summary_row['Total Debit']
    total_credit = summary_row['Total Credit']
    closing_balance = summary_row['Closing Balance']
    
    # Initialize variables for processing transactions
    transactions = []
    header_found = False
    column_indices = {
        'date': None,
        'desc': None,
        'debit': None,
        'credit': None
    }
    

    for row in rows:
        if not row or len(row) < 4:
            continue
            
        # Find header row and column indices
        if 'Transaction Date' in str(row[0]) and not header_found:
            for i, cell in enumerate(row):
                cell = str(cell).lower()
                if 'date' in cell:
                    column_indices['date'] = i
                elif 'particulars' in cell:
                    column_indices['desc'] = i
                elif 'debit' in cell:
                    column_indices['debit'] = i
                elif 'credit' in cell:
                    column_indices['credit'] = i
            header_found = True
            continue
            
        # Skip if headers haven't been found yet
        if not header_found:
            continue
            
        # Process transaction row
        try:
            date_str = row[column_indices['date']]
            date = parse_date(date_str)
            
            if not date:  
                continue
                
            description = row[column_indices['desc']]
            debit_amt = parse_amount(row[column_indices['debit']])
            credit_amt = parse_amount(row[column_indices['credit']])
            
            # Amount is negative for debits, positive for credits
            amount = credit_amt - debit_amt
            
            transaction = {
                'date': date,
                'description': description.strip(),
                'amount': amount
            }
            
            transactions.append(transaction)
            
        except Exception as e:
            print(f"Error processing row: {row}")
            print(f"Error: {str(e)}")
            continue
    
    result = {
        'statement_info': {
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_debit': total_debit,
            'total_credit': total_credit
        },
        'transactions': transactions
    }
    
    return result

def format_currency(amount):
    """Helper function to format currency values"""
    return '{:.2f}'.format(amount)

def process_idfc_statement(pdf_path):
    """
    Main function to process IDFC bank statement PDF
    Returns: JSON string of parsed data
    """
    try:
        result = parse_idfc_statement(pdf_path)
        
        # Convert to JSON string with proper formatting
        return json.dumps(result, indent=2, default=format_currency)
        
    except Exception as e:
        return json.dumps({
            'error': f'Failed to process statement: {str(e)}'
        }, indent=2)
