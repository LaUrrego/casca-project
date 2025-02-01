from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import json
from combined_check_transaction_parser import extract_text_from_pdf
from idfc_parser import parse_idfc_statement
from lloyds_parser import parse_lloyds_statement
from us_bank_parser import parse_us_bank_statement, process_document
from commonwealth_bank_parser import parse_full_featured_statement
from general_bank_parser import parse_unknown_statement
from sample_ml import BetterTransactionClassifier
from analysis import analyze_transactions
import os
import shutil

app = FastAPI()

classifier = BetterTransactionClassifier()
classifier.train_classifier("trainingdata.csv")

# Known identifiers based on statement text
def determine_bank(text):
    text_lower = text.lower()
    if "lloyds" in text_lower:
        return "Lloyds"
    elif "usbank" in text_lower:
        return "US Bank"
    elif "commbank" in text_lower:
        return "Commonwealth Bank"
    elif "idfc first" in text_lower:
        return "IDFC"
    else:
        return "Unknown"

# Dispatcher to call the appropriate parser
def parse_statement(pdf_path, bank_type):
    if bank_type == "Lloyds":
        return parse_lloyds_statement(pdf_path)
    elif bank_type == "US Bank":
        try:
            # Get main statement data
            statement_data = parse_us_bank_statement(pdf_path)
            if not isinstance(statement_data, dict):
                statement_data = json.loads(statement_data)
            
            # Get check data and extend the original data
            check_data = process_document(pdf_path, "output")
            statement_data['transactions'].extend(check_data['transactions'])
            
            return statement_data
            
        except Exception as e:
            print(f"Error processing US Bank statement: {str(e)}")
            return {
                'statement_info': {},
                'transactions': []
            }
    elif bank_type == "Commonwealth Bank":
        return parse_full_featured_statement(pdf_path)
    elif bank_type == "IDFC":
        return parse_idfc_statement(pdf_path)
    elif bank_type == "Unknown":
        return parse_unknown_statement(pdf_path)
    else:
        return {"error": "Unsupported bank type", "transactions": []}

# API endpoint to process the uploaded PDF
@app.post('/process-statement')
async def process_statement(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are supported.")

    # Save the uploaded file temporarily
    pdf_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_text = extract_text_from_pdf(pdf_path)
    bank_type = determine_bank(extracted_text)

    parsed_data = parse_statement(pdf_path, bank_type)
    if "error" in parsed_data:
        raise HTTPException(status_code=400, detail=parsed_data["error"])

    # Ensure we have a transactions list before categorization
    if 'transactions' not in parsed_data:
        parsed_data['transactions'] = []

    categorized_transactions = classifier.predict_categories(parsed_data['transactions'])
    print("these are categorized: ", categorized_transactions)
    # Clean up check data:
    # - Only keep image_file for to_review category
    # - Empty string for check_no and image_file for non-check transactions
    for txn in categorized_transactions:
        if txn.get('category') != 'to_review':
            txn['check_no'] = ""
            txn['image_file'] = ""

    analysis_result = analyze_transactions(categorized_transactions)

    # Add balances from parsed data if available
    analysis_result['statement_info'] = parsed_data.get('statement_info', {})

    def clean_json_values(data):
        if isinstance(data, dict):
            return {k: clean_json_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [clean_json_values(v) for v in data]
        elif isinstance(data, float):
            if data != data or data == float('inf') or data == float('-inf'):
                return 0.0
            return data
        elif data is None:
            return ''
        return data

    cleaned_result = clean_json_values(analysis_result)
    return JSONResponse(content=cleaned_result)

# API endpoint for handling special US Bank transactions to be reviewed from check image data
@app.post('/update-transaction')
async def update_transaction(data: dict):
    transaction = data.get('transaction')
    if not transaction:
        raise HTTPException(status_code=400, detail="Invalid input")


    date = transaction.get('date')
    description = transaction.get('description')
    amount = transaction.get('amount')
    category = transaction.get('category')

    if not (description and amount and category):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Update the model with new data
    new_training_data = [{
        "date": date,
        "description": description,
        "amount": float(amount),
        "label": category
    }]
    classifier.update_model(new_training_data)

    return JSONResponse(content={"message": "Model Updated!"})

