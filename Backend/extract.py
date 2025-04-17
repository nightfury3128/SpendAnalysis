import logging
import re 
import json
import io
import csv
import pdfplumber
from date import format_date
import os 
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="📘 [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def extract_transactions_chase_card(text, filename):
    logger.info("🔍 Matched extractor: Chase Credit Card")
    bank_name = "Chase Credit Card"
    transactions = []
    for line in text.splitlines():
        match = re.match(r"^(\d{2}/\d{2})\s+(.*?)\s+(\d+\.\d{2})$", line.strip())
        if match:
            date, desc, amount = match.groups()
            clean_desc = " ".join(desc.split())
            date = format_date(date.strip(), filename)
            transactions.append([date, amount, "Purchase", clean_desc, bank_name])
    return transactions

def extract_transactions_pnc(text, filename):
    bank_name = "PNC"
    transactions = []
    sections = {
        "Deposits and Other Additions": r"Deposits and Other Additions.*?Date Amount Description(.*?)Banking/Debit Card Withdrawals",
        "Banking/Debit Card Withdrawals and Purchases": r"Banking/Debit Card Withdrawals.*?Date Amount Description(.*?)Online and Electronic Banking Deductions",
        "Online and Electronic Banking Deductions": r"Online and Electronic Banking Deductions.*?Date Amount Description(.*?)(?:Daily Balance|Page \d+ of \d+)"
    }

    for trans_type, pattern in sections.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            section_text = match.group(1)
            entries = re.findall(r"(\d{2}/\d{2})\s+([\d,.]+)\s+(.+?)(?=\n\d{2}/\d{2}|\Z)", section_text, re.DOTALL)
            for date, amount, desc in entries:
                clean_desc = " ".join(desc.split())
                date = format_date(date.strip(), filename)
                transactions.append([date.strip(), amount.replace(",", ""), trans_type, clean_desc, bank_name])
    return transactions


def extract_transactions_chase_bank(text, filename):
    bank_name = "Chase"
    transactions = []
    entries = re.findall(r"(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})(?:\s+[\d,]+\.\d{2})?", text)
    for date, desc, amount in entries:
        clean_desc = " ".join(desc.split())
        type_ = "Credit" if "-" not in amount else "Debit"
        date = format_date(date.strip(), filename) 
        transactions.append([date.strip(), amount.replace(",", ""), type_, clean_desc, bank_name])
    return transactions

def extract_transactions_chase_card(text, filename):
    bank_name = "Chase Credit Card"
    transactions = []

    for line in text.splitlines():
        line = line.strip()
        # Match line with MM/DD followed by description and ending with an amount
        match = re.match(r"^(\d{2}/\d{2})\s+(.*?)\s+(\d+\.\d{2})$", line)
        if match:
            date, desc, amount = match.groups()
            clean_desc = " ".join(desc.split())
            type_ = "Purchase"  # These statements typically don’t show credits here
            date = format_date(date.strip(), filename)  
            transactions.append([date, amount, type_, clean_desc, bank_name])

    return transactions

def extract_transactions_discover_card(text, filename):
    bank_name = "Discover"
    transactions = []

    # Match: Trans Date, Post Date, Description, Amount
    pattern = re.findall(
        r"(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+(.+?)\$\s*(-?\d+\.\d{2})",
        text,
        re.DOTALL
    )

    for trans_date, post_date, desc, amount in pattern:
        clean_desc = " ".join(desc.strip().split())
        type_ = "Credit" if "-" in amount else "Purchase"
        formatted_date = format_date(trans_date.strip(), filename)
        transactions.append([formatted_date, amount.replace(",", ""), type_, clean_desc, bank_name])

    return transactions

def extract_transactions_amex(text, filename):
    bank_name = "American Express"
    transactions = []

    # Extract payments and credits
    payment_section = re.search(r"Payments\s+Amount(.*?)New Charges", text, re.DOTALL)
    if payment_section:
        payments = re.findall(r"(\d{2}/\d{2}/\d{2})\*?\s+MOBILE PAYMENT - THANK YOU\s+-\$([\d,]+\.\d{2})", payment_section.group(1))
        for date, amount in payments:
            formatted_date = format_date(date.strip(), filename)
            transactions.append([formatted_date, amount.replace(",", ""), "Payment", "MOBILE PAYMENT - THANK YOU", bank_name])

    # Extract purchases
    purchases = re.findall(r"(\d{2}/\d{2}/\d{2})\s+(.+?)\s+\$([\d,]+\.\d{2})", text)
    for date, desc, amount in purchases:
        clean_desc = " ".join(desc.strip().split())
        formatted_date = format_date(date.strip(), filename)
        transactions.append([formatted_date, amount.replace(",", ""), "Purchase", clean_desc, bank_name])

    return transactions

def extract_transactions_apple_card(text, filename):
    bank_name = "Apple Card"
    transactions = []

    # Extract Payments section
    payment_section = re.search(r"Payments\s+Date Description Amount(.*?)Transactions", text, re.DOTALL)
    if payment_section:
        payments = re.findall(r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+-\$(\d+\.\d{2})", payment_section.group(1))
        for date, desc, amount in payments:
            clean_desc = " ".join(desc.strip().split())
            date = format_date(date.strip(), filename)
            transactions.append([date, amount, "Payment", clean_desc, bank_name])

    # Extract Purchase Transactions
    transaction_pattern = re.findall(
        r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$\d+\.\d{2}\s+\$(\d+\.\d{2})",
        text,
        re.DOTALL
    )
    for date, desc, amount in transaction_pattern:
        clean_desc = " ".join(desc.strip().split())
        date = format_date(date.strip(), filename)
        transactions.append([date, amount, "Purchase", clean_desc, bank_name])

    return transactions

def extract_transactions_goldman_savings(text, filename):
    bank_name = "Goldman Sachs Savings"
    transactions = []

    # Match lines like: 02/02/2025 Daily Cash Deposit $9.87
    pattern = re.findall(r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+\$([\d,]+\.\d{2})", text)

    for date, desc, amount in pattern:
        clean_desc = " ".join(desc.strip().split())
        type_ = "Credit"  # All are deposits or interest, no withdrawals in this statement
        formatted_date = format_date(date.strip(), filename)
        transactions.append([formatted_date, amount.replace(",", ""), type_, clean_desc, bank_name])

    return transactions
def extract_transactions(text, filename, unknown_files):
    if "Virtual Wallet" in text or "PNC" in text:
        return extract_transactions_pnc(text, filename)
    elif "New Balance" in text and "Payment Due Date" in text:
        return extract_transactions_chase_card(text, filename)
    elif "JPMorgan" in text or "Chase.com" in text:
        return extract_transactions_chase_bank(text, filename)
    elif "Discover" in text and "Activity Period" in text:
        return extract_transactions_discover_card(text, filename)
    elif "American Express" in text and "SkyMiles" in text:
        return extract_transactions_amex(text, filename)
    elif "Apple Card is issued by Goldman Sachs Bank USA" in text:
        return extract_transactions_apple_card(text, filename)
    elif "Goldman Sachs Bank USA" in text and "Daily Cash Deposit" in text:
        return extract_transactions_goldman_savings(text, filename)

    else:
        print(f"⚠️ Unknown format in: {filename}")
        unknown_files.append(filename)
        return []


# --- Main Processing Function ---
def process_all_pdfs(folder_path, output_csv):
    all_transactions = []
    unknown_files = []

    for file in Path(folder_path).glob("*.pdf"):
        try:
            with pdfplumber.open(file) as pdf:
                text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                transactions = extract_transactions(text, file.name, unknown_files)
                all_transactions.extend(transactions)
        except Exception as e:
            logger.error(f"Failed to process {file.name}: {e}")
            unknown_files.append(file.name)

    # Save all to CSV
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Amount", "Type", "Description", "Bank"])
        writer.writerows(all_transactions)

    logger.info(f"✅ Extraction complete. Saved to {output_csv}")
    if unknown_files:
        logger.warning(f"⚠️ Unknown formats in: {unknown_files}")

# --- Usage Example ---
if __name__ == "__main__":
    process_all_pdfs("Dataset", "Dataset/account.csv")