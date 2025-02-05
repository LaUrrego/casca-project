from collections import defaultdict
from typing import List, Dict, Any

def analyze_transactions(
    classified_data: List[Dict[str, Any]], 
    opening_balance=0.0, 
    closing_balance=0.0
) -> Dict[str, Any]:
    """
    Perform post-processing analysis on already-classified transactions.
    Returns a dictionary suitable for JSON output, which includes:
      1) summary stats (total income, expenses, net change, largest in/out)
      2) category breakdown
      3) unusual and recurring transactions
      4) the full list of classified transactions
    """

    total_income = 0.0
    total_expenses = 0.0
    category_sums = defaultdict(float)

    largest_expense = {"amount": 0.0, "description": "", "date": ""}
    largest_income = {"amount": 0.0, "description": "", "date": ""}

    unusual_transactions = []

    recurring_spend = 0.0
    recurring_items = []

    for tx in classified_data:
        # Convert 'amount' from string to float if needed
        amount = float(tx["amount"])
        cat = tx["category"]

        # Identify inflow vs. outflow
        if amount < 0:
            abs_amt = abs(amount)
            total_expenses += abs_amt
            category_sums[cat] += abs_amt
            # Check if it's the largest expense so far
            if abs_amt > largest_expense["amount"]:
                largest_expense = {
                    "amount": abs_amt,
                    "description": tx["description"],
                    "date": tx["date"]
                }
        else:
            total_income += amount
            category_sums[cat] += amount
            # Check if it's the largest income so far
            if amount > largest_income["amount"]:
                largest_income = {
                    "amount": amount,
                    "description": tx["description"],
                    "date": tx["date"]
                }

        # Check if flagged as unusual
        if tx.get("is_unusual") == 1:
            unusual_transactions.append(tx)

        # Check if flagged as recurring (model or dictionary might prefix the category with "recurring_")
        # OR if 'is_recurring' == 1
        if "recurring_" in cat or tx.get("is_recurring") == 1:
            if amount < 0:
                recurring_spend += abs(amount)
            recurring_items.append(tx)

    # Calculate net change
    net_change = total_income - total_expenses
    

    if opening_balance and closing_balance:
        actual_balance_change = closing_balance - opening_balance
        balance_discrepancy = round(net_change - actual_balance_change, 2)
    else:
        balance_discrepancy = None


    analysis = {
        "summary": {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_change": round(net_change, 2),
            "largest_expense": largest_expense,
            "largest_income": largest_income,
            "balance_discrepancy": balance_discrepancy
        },
        "category_breakdown": {
            cat: round(amt, 2)
            for cat, amt in category_sums.items()
        },
        "unusual_transactions": unusual_transactions,
        "recurring_summary": {
            "total_recurring_spend": round(recurring_spend, 2),
            "recurring_transactions": recurring_items
        },

        "all_transactions": classified_data
    }

    return analysis
