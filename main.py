import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from datetime import datetime, timedelta
import json

# Initialize Plaid API
client_id = 'your_client_id'
secret = 'your_secret'
PLAID_ENV = plaid.Environment.Sandbox

configuration = plaid.Configuration(
    host=PLAID_ENV,
    api_key={
        'clientId': client_id,
        'secret': secret,
    }
)
api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# Load whitelist from JSON file and convert all entries to uppercase
def load_whitelist(whitelist_file):
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)
    return [entry.upper() for entry in whitelist]  # Normalize whitelist by converting to uppercase

# Function to retrieve transactions from Plaid API
def get_transactions(access_token, start_date, end_date):
    options = TransactionsGetRequestOptions(count=100)  # Retrieve the first 100 transactions
    request = TransactionsGetRequest(
        access_token=access_token,
        start_date=start_date,
        end_date=end_date,
        options=options
    )
    response = client.transactions_get(request)
    return response['transactions']

# Process recurring transactions with the same amount and whitelist filtering
def find_recurring_transactions(transactions, whitelist):
    transaction_map = {}

    for transaction in transactions:
        name = transaction['name'].upper()  # Normalize transaction name to uppercase
        amount = transaction['amount']
        date = datetime.strptime(transaction['date'], '%m/%d/%Y')  # Assume date format is MM/DD/YYYY

        # Check if transaction name contains any whitelisted term (allow spaces and case-insensitivity)
        if any(whitelisted_term in name for whitelisted_term in whitelist):
            continue  # Skip whitelisted transactions

        # Add transaction to the transaction map
        if name in transaction_map:
            transaction_map[name]['amounts'].append(amount)
            transaction_map[name]['dates'].append(date)
        else:
            transaction_map[name] = {'amounts': [amount], 'dates': [date]}

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

# Main function to run on the 15th of every month
def run_monthly_check():
    # Dynamic date calculation
    start_date = (datetime.today() - timedelta(days=90)).date().isoformat()  # 90 days back
    end_date = datetime.today().date().isoformat()  # Today's date

    # Exchange the public token (in a real app, this would be stored securely)
    public_token = 'your_public_token'
    access_token = exchange_public_token(public_token)

    # Get transactions from Plaid API
    transactions = get_transactions(access_token, start_date, end_date)

    # Load whitelist
    whitelist = load_whitelist('/app/whitelist.json')

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

# Exchange the public token for an access token
def exchange_public_token(public_token):
    exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
    exchange_response = client.item_public_token_exchange(exchange_request)
    return exchange_response['access_token']

# Run the monthly check
if __name__ == "__main__":
    run_monthly_check()  # For testing purposes, run immediately
