import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from flask import Flask, jsonify, request, render_template
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)

# Initialize Plaid API client
client_id = os.getenv('PLAID_CLIENT_ID')
secret = os.getenv('PLAID_SECRET')
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

# Serve the frontend HTML that integrates Plaid Link
@app.route('/')
def index():
    return render_template('index.html')

# Route to create a Link token
@app.route('/create_link_token', methods=['POST'])
def create_link_token():
    try:
        user = {"client_user_id": "unique_user_id"}  # Replace with real user ID
        request = LinkTokenCreateRequest(
            products=['auth', 'transactions'],  # Add the Plaid products you want to use
            client_name="Your App Name",
            country_codes=['US'],
            language='en',
            user=user
        )
        response = client.link_token_create(request)

        # Send the Link token back to the frontend
        return jsonify({'link_token': response['link_token']}), 200

    except plaid.ApiException as e:
        return jsonify({"error": e.body}), 500

# Route to exchange the public token for an access token
@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token():
    public_token = request.json.get('public_token')
    if not public_token:
        return jsonify({"error": "Public token not provided"}), 400

    try:
        # Exchange the public token for an access token
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']

        # In a real application, you'd store the access token securely (e.g., in a database)
        return jsonify({"access_token": access_token}), 200

    except plaid.ApiException as e:
        return jsonify({"error": e.body}), 500

# Route to fetch transactions and check recurring transactions using the access token
@app.route('/get_recurring_transactions', methods=['POST'])
def get_recurring_transactions():
    access_token = request.json.get('access_token')
    if not access_token:
        return jsonify({"error": "Access token not provided"}), 400

    try:
        # Calculate date range (last 90 days)
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')

        # Request transactions from Plaid API
        options = TransactionsGetRequestOptions(count=100)
        transactions_request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=options
        )
        transactions_response = client.transactions_get(transactions_request)

        transactions = transactions_response['transactions']

        # Load whitelist from a JSON file (you can place it in your project root)
        with open('whitelist.json', 'r') as f:
            whitelist = [entry.upper() for entry in json.load(f)]  # Case-insensitive

        # Process recurring transactions
        recurring_transactions = find_recurring_transactions(transactions, whitelist)

        return jsonify({'recurring_transactions': recurring_transactions}), 200

    except plaid.ApiException as e:
        return jsonify({"error": e.body}), 500

# Function to find recurring transactions with the same amount, excluding those in the whitelist
def find_recurring_transactions(transactions, whitelist):
    transaction_map = {}

    for transaction in transactions:
        name = transaction['name'].upper()  # Normalize transaction name to uppercase
        amount = transaction['amount']
        date = datetime.strptime(transaction['date'], '%Y-%m-%d')  # Assuming date format

        # Skip whitelisted transactions
        if any(whitelisted_term in name for whitelisted_term in whitelist):
            continue

        if name in transaction_map:
            transaction_map[name]['amounts'].append(amount)
            transaction_map[name]['dates'].append(date)
        else:
            transaction_map[name] = {'amounts': [amount], 'dates': [date]}

    # Filter to keep only transactions with the same amount more than once
    recurring_transactions = {
        name: {
            'amounts': data['amounts'],
            'last_date': max(data['dates']).strftime('%Y-%m-%d')  # Get latest transaction date
        }
        for name, data in transaction_map.items()
        if len(data['amounts']) > 1 and len(set(data['amounts'])) == 1
    }

    return recurring_transactions

# Entry point for running the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8777, debug=True)
