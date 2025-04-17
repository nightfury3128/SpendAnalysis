from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # Import CORS
from functools import wraps
import io
import csv
import pdfplumber
import re
import os
import logging
from flask_caching import Cache
from dashboard import generate_dashboard, forecast_spending
from extract import extract_transactions
import datetime

# Import configuration from utils instead of loading directly
from utils import CONFIG

app = Flask(__name__)
# Enable CORS with more permissive settings
CORS(app, supports_credentials=True, expose_headers=['X-API-Key'])

API_KEY = CONFIG.get("API_KEY", "")
CSV_FILE = CONFIG.get("CSV_FILE", "Dataset/account.csv")

# Cache configuration
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes cache timeout
})

# -----------------------
# Logging Configuration
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="📘 [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Log the configured API key (masked for security) for debugging
if API_KEY:
    masked_api_key = API_KEY[:2] + '*' * (len(API_KEY)-4) + API_KEY[-2:] if len(API_KEY) > 3 else '***'
    logger.info(f"🔑 Configured API key: {masked_api_key}")
else:
    logger.warning("⚠️ No API key configured in creds.json")

# -----------------------
# Custom Jinja2 filters and context
# -----------------------
@app.template_filter('now')
def _jinja2_filter_now(fmt):
    return datetime.datetime.now().strftime(fmt)

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

# -----------------------
# Access Information
# -----------------------
def get_ip_address():
    """Get the local IP address to help users connect from other devices"""
    import socket
    try:
        # Get the host name
        hostname = socket.gethostname()
        # Get the IP address
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception:
        return "Could not determine IP address"

# -----------------------
# Token-Based Auth
# -----------------------
def requires_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-API-Key")
        if not token:
            logger.warning("🔐 No API key provided in request.")
            return jsonify({"error": "API key required"}), 401
            
        if token != API_KEY:
            # Log part of received token for debugging (masked for security)
            masked_token = token[:2] + '*' * (len(token)-4) + token[-2:] if len(token) > 3 else '***'
            logger.warning(f"🔐 Invalid API key provided: {masked_token} vs expected: {masked_api_key}")
            return jsonify({"error": "Invalid API key"}), 401
            
        return f(*args, **kwargs)
    return decorated

# -----------------------
# API Key Check Endpoint
# -----------------------
@app.route("/api-key-check", methods=["GET"])
def check_api_key():
    token = request.headers.get("X-API-Key")
    if not token:
        logger.warning("🔐 API key check: No API key provided")
        return jsonify({"valid": False, "error": "No API key provided"}), 401
    
    valid = token == API_KEY
    if valid:
        logger.info("✅ API key check: Valid key")
    else:
        masked_token = token[:2] + '*' * (len(token)-4) + token[-2:] if len(token) > 3 else '***'
        logger.warning(f"❌ API key check: Invalid key {masked_token}")
        
    return jsonify({"valid": valid})

# -----------------------
# Upload Endpoint
# -----------------------
@app.route("/upload", methods=["POST"])
@requires_api_key
def upload_pdf():
    file = request.files.get("file")

    if not file:
        logger.warning("📎 No file in request.")
        return jsonify({"error": "No file provided"}), 400

    if not file.filename.lower().endswith(".pdf"):
        logger.warning("⛔ Uploaded file is not a PDF.")
        return jsonify({"error": "File is not a PDF"}), 400

    try:
        logger.info(f"📥 Received file: {file.filename}")
        pdf_bytes = file.read()

        # Extract text from PDF
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )


        # Extract transactions
        unknown_files = []
        transactions = extract_transactions(full_text, file.filename, unknown_files)

        if not transactions:
            logger.warning(f"⚠️ No transactions extracted from: {file.filename}")
            return jsonify({"error": f"Could not process file: {file.filename}"}), 422

        # Append to CSV
        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Date", "Amount", "Type", "Description", "Bank"])
            writer.writerows(transactions)

        logger.info(f"✅ Saved {len(transactions)} transactions from: {file.filename}")
        return jsonify({
            "message": f"Processed and saved {len(transactions)} transactions.",
            "filename": file.filename
        })

    except Exception as e:
        logger.exception("💥 Unexpected error during PDF processing.")
        return jsonify({"error": str(e)}), 500

# -----------------------
# Dashboard Endpoint
# -----------------------
@app.route("/dashboard", methods=["GET"])
@requires_api_key
@cache.cached(timeout=300)
def dashboard_data():
    try:
        # Check if CSV file exists
        if not os.path.isfile(CSV_FILE):
            return jsonify({"error": "No transaction data found"}), 404
            
        # Generate dashboard data
        dashboard = generate_dashboard(CSV_FILE)
        return jsonify(dashboard)
        
    except Exception as e:
        logger.exception("Error generating dashboard data")
        return jsonify({"error": str(e)}), 500

# -----------------------
# Run the server
# -----------------------
if __name__ == "__main__":
    ip_address = get_ip_address()
    logger.info(f"🚀 Starting server on http://{ip_address}:5000")
    app.run(debug=True, host="0.0.0.0")

