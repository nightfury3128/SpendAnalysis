from flask import Flask, request, jsonify, render_template
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

# Import configuration from utils instead of loading directly
from utils import CONFIG

app = Flask(__name__)
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

# -----------------------
# Token-Based Auth
# -----------------------
def requires_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-API-Key")
        if not token or token != API_KEY:
            logger.warning("🔐 Unauthorized access attempt.")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


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
# Frontend Route
# -----------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/dashboard")
@cache.cached(timeout=300)  # Cache for 5 minutes
def dashboard():
    try:
        # Get all visualizations and data from generate_dashboard
        dashboard_data = generate_dashboard(CSV_FILE)
        
        # Log what keys are available for debugging
        logger.info(f"Dashboard data keys: {list(dashboard_data.keys())}")
        
        # Add some basic validation to ensure key values exist
        if not dashboard_data.get("summary_stats"):
            dashboard_data["summary_stats"] = {
                "total_income": 0, 
                "total_papa_transfer": 0,
                "total_expenses": 0, 
                "savings": 0, 
                "savings_rate": 0
            }
        
        return render_template(
            "dashboard.html",
            pie_chart=dashboard_data.get("pie_chart", ""),
            bar_chart=dashboard_data.get("bar_chart", ""),
            forecast=dashboard_data.get("forecast", ""),
            income_vs_expenses=dashboard_data.get("income_vs_expenses", ""),
            essential_ratio=dashboard_data.get("essential_ratio", ""),
            dining_vs_groceries=dashboard_data.get("dining_vs_groceries", ""),
            calendar=dashboard_data.get("calendar", ""),
            top_categories=dashboard_data.get("top_categories", ""),
            category_growth=dashboard_data.get("category_growth", ""),
            income_flow=dashboard_data.get("income_flow", ""),
            rent_forecast=dashboard_data.get("rent_forecast", ""),
            food_forecast=dashboard_data.get("food_forecast", ""),
            transaction_table=dashboard_data.get("transaction_table", ""),
            summary_stats=dashboard_data["summary_stats"],
            total_income=dashboard_data["summary_stats"].get("total_income", 0)
        )
    except Exception as e:
        logger.exception(f"Error in dashboard route: {str(e)}")
        # Return a simple error page if something goes wrong
        return f"<h1>Dashboard Error</h1><p>{str(e)}</p>"

# -----------------------
# Run the App
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)