# casca-project

# backend 
An intelligent system that combines bank statement parsing, machine learning classification, and financial analysis to provide automated transaction categorization and spending insights.
Features

## Multi-Bank Support

- Commonwealth Bank: Full-featured parser with text alignment and multi-line transaction support
- Lloyds Bank: Payment code detection system with UK-specific date formats
- US Bank: Integrated check processing with section-based parsing
- IDFC Bank: Table-based layout parsing 
- General Parser: Fallback system with dynamic column detection for unknown formats, modeled after the Commonwealth Bank parser

## ML-Powered Transaction Classification 
The system employs a three-layer classification approach:

- Known Vendor Matching

    - Dictionary-based instant classification
    - High-precision vendor recognition


- Machine Learning Classification

    - Random Forest classifier
    - TF-IDF vectorization for transaction descriptions
    - Standardized amount scaling
    - Continuous learning from user corrections


- Pattern Detection

    - Recurring payment identification
    - Anomaly detection using IsolationForest
    - Transaction pattern analysis



## Financial Analysis 

- Category-wise spending breakdown
- Recurring payment tracking
- Unusual transaction detection
- Balance verification and reconciliation
- Comprehensive transaction history

## Installation

```
# Clone repository
git clone [repository-url]

# Move into backend
cd backend

# Install dependencies
pip install -r requirements.txt
```

## Usage
### Starting the Server

```
uvicorn unified_backend_mvp:app --reload
```

## API Endpoints
### Process Statement

```
curl -X POST http://127.0.0.1:8000/process-statement \
    -F 'file=@statement.pdf'


Response:
{
    "statement_info": {
        "opening_balance": float,
        "closing_balance": float
    },
    "transactions": [
        {
            "date": string,
            "description": string,
            "amount": float,
            "category": string,
            "is_recurring": boolean,
            "is_unusual": boolean
        }
    ],
    "analysis": {
        "category_breakdown": object,
        "recurring_summary": object,
        "unusual_transactions": array
    }
}
```

## Update Transaction Category

```
curl -X POST http://127.0.0.1:8000/update-transaction \
     -H "Content-Type: application/json" \
     -d '{
           "transaction": {
             "check_no": "12345",
             "date": "2025-02-04",
             "description": "Payment for services",
             "amount": "100.00",
             "category": "Business Expense",
             "image_file": "receipt.jpg",
             "is_unusual": true
           }
         }'


Response:
{"message": "Model Updated!"}
```

# Technical Requirements
## Core Dependencies

- Python 3.8+
- FastAPI
- pdfplumber
- scikit-learn
- pandas
- numpy

## ML Model Requirements

- TensorFlow (optional, for future neural network implementations)
- scikit-learn 1.0+
- numpy 1.20+

# Model Training
## Initial Training
```
# Train the initial model
python ml_transaction_classifier.py

# Model automatically updates through the /update-transaction endpoint
```

# Continuous Learning
The system learns from user corrections through:

- Transaction correction submissions
- Model retraining with updated dataset
- Accuracy improvement tracking

# Current Limitations
- System is intended for submissions of original, text-based PDF documents, no scanned versions. This initial MVP is to function with the limitations of being bank worker that only has access to an initial set of 4 different statements. 
- Single transaction corrections only. Updates send user-labeled transactions and save them to the training CSV, calling the model to be retrained on the new dataset. This works fine for this current iteration, but would be slow as the dataset grows. 
- No undo function for corrections. 
- Limited currency support to handle current bank statements plus a few more. 