import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.country_code import CountryCode
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Plaid API configuration
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

# User model for storing client_user_id and access_token
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_user_id = db.Column(db.String(50), unique=True, nullable=False)
    access_token = db.Column(db.String(255), nullable=False)

# Ensure tables are created before the first request
with app.app_context():
    db.create_all()

# Serve the frontend HTML that integrates Plaid Link
@app.route('/')
def index():
    return render_template('index.html')

# Route to create a Link token
@app.route('/create_link_token', methods=['POST'])
def create_link_token():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()  # Safely extract JSON data
    user_id = data.get('user_id')  # Assuming frontend sends this

    if not user_id:
        return jsonify({"error": "User ID not provided"}), 400

    # Check if the user exists in the database
    user = User.query.filter_by(client_user_id=user_id).first()
    if not user:
        # If user doesn't exist, create a new user with a placeholder access token
        user = User(client_user_id=user_id, access_token="placeholder_token")
        db.session.add(user)
        db.session.commit()

    try:
        # Create a Link Token request using the user's ID
        request_data = LinkTokenCreateRequest(
            products=['auth', 'transactions'],  # Use lowercase strings for products
            client_name="Your App Name",
            country_codes=[CountryCode('US')],
            language='en',
            user={"client_user_id": user_id}
        )
        response = client.link_token_create(request_data)

        # Send the Link token back to the frontend
        return jsonify({'link_token': response['link_token']}), 200

    except plaid.ApiException as e:
        return jsonify({"error": e.body}), 500

# Route to exchange the public token for an access token
@app.route('/exchange_public_token', methods=['POST'])
def exchange_public_token():
    data = request.get_json()
    public_token = data.get('public_token')
    user_id = data.get('user_id')  # We expect user_id to be passed

    if not public_token or not user_id:
        return jsonify({"error": "Public token or User ID not provided"}), 400

    try:
        # Exchange the public token for an access token
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']

        # Update the user record with the access token
        user = User.query.filter_by(client_user_id=user_id).first()
        if user:
            user.access_token = access_token
            db.session.commit()
        else:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"access_token": access_token}), 200

    except plaid.ApiException as e:
        return jsonify({"error": e.body}), 500

# Route to fetch transactions and check recurring transactions using the access token
@app.route('/get_recurring_transactions', methods=['POST'])
def get_recurring_transactions():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID not provided"}), 400

    # Fetch the user and access token from the database
    user = User.query.filter_by(client_user_id=user_id).first()

    if not user or not user.access_token:
        return jsonify({"error": "Access token not found for user"}), 404

    try:
        # Calculate date range (last 90 days)
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')

        # Request transactions from Plaid API
        options = TransactionsGetRequestOptions(count=100)
        transactions_request = TransactionsGetRequest(
            access_token=user.access_token,
            start_date=start_date,
            end_date=end_date,
            options=options
        )
        transactions_response = client.transactions_get(transactions_request)

        transactions = transactions_response['transactions']

        # Load whitelist from a JSON file
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
