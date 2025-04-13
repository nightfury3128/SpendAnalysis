from flask import Flask, request, jsonify, render_template
from functools import wraps
import io
import csv
import pdfplumber
import re
import os
import logging
import json 
from dashboard import generate_dashboard
from extract import extract_transactions


with open ("creds.json") as creds:
    config = json.load(creds)


app = Flask(__name__)
API_KEY = config["API_KEY"]  
CSV_FILE = config["CSV_FILE"] 

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
def dashboard():
    return generate_dashboard()

# -----------------------
# Run the App
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
