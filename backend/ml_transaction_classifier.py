import numpy as np
import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Tuple
import os

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


class MLTransactionClassifier:
    def __init__(self):
        """
        Constructor sets up dictionary-based rules, isolation forest
        """
        self.model = None  
        self.description_vectorizer = TfidfVectorizer(max_features=500, ngram_range=(1, 2))
        self.scaler = StandardScaler()
        
        # Outlier detection
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        
        # Known vendors dictionary with categories that match the training CSV labels (all lowercase)
        self.known_vendors = {
            'utilities': {
                'telstra': ['TELSTRA'],
                'vodafone': ['VODAFONE'],
                'verizon': ['VERIZON'],
                'at&t': ['AT&T', 'ATT'],
                't-mobile': ['T-MOBILE', 'TMOBILE'],
                'synergy': ['SYNERGY'],
                'alinta': ['ALINTA']
            },
            'insurance': {
                'sgio': ['SGIO'],
                'hbf': ['HBF'],
                'aami': ['AAMI']
            },
            'dining': {
                'mcdonalds': ['MCDONALDS', 'MCDONALD\'S', 'MCD'],
                'subway': ['SUBWAY'],
                'kfc': ['KFC'],
                'burger king': ['BURGER KING', 'BK']
            },
            'recurring_payment': {
                'jetts': ['JETTS'],
                'planet fitness': ['PLANETFITNESS', 'PLANET FITNESS'],
                'netflix': ['NETFLIX'],
                'spotify': ['SPOTIFY'],
                'disney plus': ['DISNEY+', 'DISNEY PLUS']
            },
            'shopping': {
                'amazon': ['AMAZON', 'AMZN'],
                'nike': ['NIKE','nike','Nike']
            }
        }
    
    def train_classifier(self, csv_path: str) -> None:
        """
        Train a supervised model (RandomForest) on labeled transactions.
        Expects a CSV with columns: date, description, amount, label
        Taken from a first-pass at the extracted transactions in the 4 documents. 
        """
        df = pd.read_csv(csv_path)
        
        # Basic cleaning
        df['description'] = df['description'].astype(str).fillna('')
        df['amount'] = df['amount'].astype(float)
        
        # Text features
        X_text = self.description_vectorizer.fit_transform(df['description'])
        
        # Numeric features: transaction amount, scaled
        amounts = df[['amount']].values
        amounts_scaled = self.scaler.fit_transform(amounts)
        
        # Combine text + numeric
        X = np.hstack([X_text.toarray(), amounts_scaled])
        
        # Labels
        y = df['label'].astype(str).values
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train random forest
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Quick evaluation
        y_pred = self.model.predict(X_test)
        print("Classification Report (on held-out test data):")
        print(classification_report(y_test, y_pred))
        
        # Fit isolation forest (for anomalies)
        self.isolation_forest.fit(X_train)

    def identify_vendor(self, description: str) -> Tuple[str, str]:
        """
        Check if description matches any known vendor;
        return (category, vendor_name) or (None, None).
        """
        desc_upper = description.upper()
        for category, vendor_dict in self.known_vendors.items():
            for vendor_name, patterns in vendor_dict.items():
                if any(pattern.upper() in desc_upper for pattern in patterns):
                    return category, vendor_name
        return None, None

    def find_recurring_patterns(self, transactions: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Identify recurring transactions from a list of dicts
        with keys: date, description, amount, etc.
        """
        df = pd.DataFrame(transactions)
        if 'amount' not in df.columns:
            df['amount'] = 0.0
        
        def extract_merchant(desc):
            # Remove digits and some known keywords
            desc = desc.upper()
            desc = re.sub(r'\d+', '', desc)
            desc = re.sub(r'DIRECT DEBIT|DIRECT CREDIT|NETBANK|BPAY|TRANSFER|TO|FROM', '', desc)
            return ' '.join(desc.split())
        
        df['merchant'] = df['description'].apply(extract_merchant)
        
        recurring = {}
        for merchant, group in df.groupby('merchant'):
            if len(group) < 2:
                continue  
            
            amounts = group['amount'].values
            # Attempt to parse date as day+month, ignoring year
            dates = []
            for d in group['date']:
                try:
                    dt = datetime.strptime(d, '%d %b')
                    dates.append(dt)
                except:
                    pass
            
            # Check intervals if we have at least 2 valid parsed dates
            if len(dates) >= 2:
                date_diffs = np.diff([dt.toordinal() for dt in dates]) 
                # Heuristic: stdev of intervals < 5 => consistent timing
                if len(date_diffs) > 0:
                    regular_timing = np.std(date_diffs) < 5
                else:
                    regular_timing = False
            else:
                regular_timing = False
            
            # Check for consistent amounts
            amount_mean = np.mean(abs(amounts))
            amount_std = np.std(abs(amounts))
            consistent_amount = False
            if amount_mean != 0:
                ratio = amount_std / amount_mean
                consistent_amount = (ratio < 0.1)
            
            # If it meets both criteria, consider it recurring
            if regular_timing and consistent_amount:
                recurring[merchant] = group.to_dict('records')
        
        return recurring

    def predict_categories(self, new_transactions: List[Dict]) -> List[Dict]:
        """
        Classify new transactions using the trained model,
        then override with known vendor categories, plus detect unusual & recurring patterns.
        """
        print("We entered predict_cat")
        if not self.model:
            raise ValueError("Model is not trained. Call train_classifier(csv_path) first.")

        # Convert to DataFrame to handle them easily
        df = pd.DataFrame(new_transactions)

        # Ensure 'amount' is present
        if 'amount' not in df.columns:
            df['amount'] = 0.0

        # Identify recurring patterns (based on date, description, amount)
        recurring = self.find_recurring_patterns(new_transactions)

        # Build feature matrix for classification
        descriptions = df['description'].astype(str).fillna('').tolist()
        X_text = self.description_vectorizer.transform(descriptions)
        amounts = df[['amount']].astype(float).values
        amounts_scaled = self.scaler.transform(amounts)
        X = np.hstack([X_text.toarray(), amounts_scaled])

        # Model predictions
        predicted_labels = self.model.predict(X)

        # Isolation Forest anomaly detection
        # -1 => anomaly, 1 => normal
        anomaly_flags = self.isolation_forest.predict(X)  

        # Construct final classification with overrides
        classified = []
        for i, row in df.iterrows():
            description = row.get('description', '')
            base_label = predicted_labels[i]

            # If description is empty => "to_review"
            if not description.strip():
                final_label = "to_review"
            else:
                # Dictionary-based override
                known_cat, known_vendor = self.identify_vendor(description)
                if known_cat is not None:
                    final_label = known_cat  # e.g. "utilities", "dining", etc.
                else:
                    final_label = base_label.lower()

            # Check for recurring
            merchant_key = re.sub(r'\d+', '', description.upper())
            merchant_key = re.sub(r'DIRECT DEBIT|DIRECT CREDIT|NETBANK|BPAY|TRANSFER|TO|FROM', '', merchant_key)
            merchant_key = ' '.join(merchant_key.split())
            is_recurring = (merchant_key in recurring)
            if is_recurring and not final_label.startswith("recurring_"):
                final_label = f"recurring_{final_label}"

            # Check for anomaly
            is_anomaly = (anomaly_flags[i] == -1)
            if is_anomaly and not final_label.startswith("unusual_"):
                final_label = f"unusual_{final_label}"

            result_record = {

                "check_no": row.get("check_no", ""),
                "image_file": row.get("image_file", ""),
                "date": row.get("date", ""),
                "description": description,
                "amount": str(row.get("amount", "0")),
                "category": final_label,
                "is_recurring": int(is_recurring),
                "is_unusual": int(is_anomaly)
            }

            classified.append(result_record)

        return classified
    
    def update_model(self, new_data: List[Dict]):
        """
        Update the model by appending new data and re-training.
        """
        # Convert new data to a DataFrame
        df_new = pd.DataFrame(new_data)

        # Append new data to the existing CSV
        existing_csv = "trainingdata.csv"
        if os.path.exists(existing_csv):
            df_existing = pd.read_csv(existing_csv)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        # Save updated dataset
        df_combined.to_csv(existing_csv, index=False)

        # Re-train the model
        self.train_classifier(existing_csv)
