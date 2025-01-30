# TO RUN: have transaction data in 'chase.csv' at root
import glob
import csv
import json
from datetime import datetime

# Load whitelist from JSON file and convert all entries to uppercase
def load_whitelist(whitelist_file):
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)
    return [entry.upper() for entry in whitelist]  # Normalize whitelist by converting to uppercase

# Function to retrieve transactions from a CSV file
def get_transactions_from_csv(csv_file):
    transactions = []
    
    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Assuming the CSV has 'Transaction Date', 'Description', and 'Amount' columns
        for row in reader:
            transactions.append({
                'name': row['Description'],
                'amount': float(row['Amount']),
                'date': datetime.strptime(row['Transaction Date'], '%m/%d/%Y')  # Corrected date format: MM/DD/YYYY
            })
            
    return transactions

# Process recurring transactions with the same amount and whitelist filtering
def find_recurring_transactions(transactions, whitelist):
    transaction_map = {}

    for transaction in transactions:
        name = transaction['name'].upper()  # Normalize transaction name to uppercase
        amount = transaction['amount']

        # Check if transaction name contains any whitelisted term (allow spaces and case-insensitivity)
        if any(whitelisted_term in name for whitelisted_term in whitelist):
            continue  # Skip whitelisted transactions

        # Add transaction to the transaction map
        if name in transaction_map:
            transaction_map[name]['amounts'].append(amount)
            transaction_map[name]['dates'].append(transaction['date'])
        else:
            transaction_map[name] = {'amounts': [amount], 'dates': [transaction['date']]}

    # Filter only those transactions that have the same amount occurring more than once
    recurring_transactions = {
        name: {
            'amounts': data['amounts'],
            'last_date': max(data['dates'])  # Get the latest date for the transaction
        }
        for name, data in transaction_map.items()
        if len(data['amounts']) > 1 and len(set(data['amounts'])) == 1
    }

    return recurring_transactions

# Main function to run the test
def run_test():
    # Load the whitelist
    whitelist = load_whitelist('whitelist.json')

    # Retrieve transactions from CSV file
    # transactions = get_transactions_from_csv('chase.csv')
    csv_files = glob.glob('[cC]*.[cC][sS][vV]') # Case insisitive glob to pick up Chase's exports
    for csv_file in csv_files:
        targetFile = csv_file
        
    transactions = get_transactions_from_csv(targetFile)

    # Find recurring transactions with the same amount
    recurring_transactions = find_recurring_transactions(transactions, whitelist)

    # Display recurring transactions
    if recurring_transactions:
        print("Recurring transactions:")
        for name, data in recurring_transactions.items():
            last_date_str = data['last_date'].strftime('%Y-%m-%d')
            print(f"{name}: {data['amounts'][-1]} (Last Transaction Date: {last_date_str})")
    else:
        print("No recurring transactions found.")

# Run the test
if __name__ == "__main__":
    run_test()
