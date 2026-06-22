from flask import Flask, request, abort
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY')

# Security middleware
@app.before_request
def require_api_key():
    auth = request.headers.get('X-API-KEY')
    if not auth or auth != API_KEY:
        abort(401)

# Example route (PUT/POST routes will inherit this check)
@app.route('/api/resource', methods=['PUT', 'POST'])
def protected_route():
    return 'API Key verified', 200