import re
import pdfplumber
import csv
import os

def extract_transactions_pnc(text):
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
                transactions.append([date.strip(), amount.replace(",", ""), trans_type, clean_desc, bank_name])
    return transactions

def extract_transactions_chase_bank(text):
    bank_name = "Chase"
    transactions = []
    entries = re.findall(r"(\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+\.\d{2})(?:\s+[\d,]+\.\d{2})?", text)
    for date, desc, amount in entries:
        clean_desc = " ".join(desc.split())
        type_ = "Credit" if "-" not in amount else "Debit"
        transactions.append([date.strip(), amount.replace(",", ""), type_, clean_desc, bank_name])
    return transactions

def extract_transactions_chase_card(text):
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
            transactions.append([date, amount, type_, clean_desc, bank_name])

    return transactions

def extract_transactions_discover_card(text):
    bank_name = "Discover"
    transactions = []

    # Pattern to match: Date, Description, Amount (may be negative)
    pattern = re.findall(
        r"(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+(.+?)\s+\$\s*(-?\d+\.\d{2})",
        text,
        re.DOTALL,
    )

    for trans_date, post_date, desc, amount in pattern:
        clean_desc = " ".join(desc.split())
        type_ = "Credit" if "-" in amount else "Purchase"
        transactions.append([trans_date, amount.replace(",", ""), type_, clean_desc, bank_name])

    return transactions

def extract_transactions_amex(text):
    bank_name = "American Express"
    transactions = []

    # Pattern to match transaction lines: MM/DD/YY Description ... $Amount
    pattern = re.findall(
        r"(\d{2}/\d{2}/\d{2})\s+(.+?)\s+\$(-?\d+\.\d{2})",
        text,
        re.DOTALL
    )

    for date, desc, amount in pattern:
        clean_desc = " ".join(desc.strip().split())
        type_ = "Credit" if "-" in amount else "Purchase"
        transactions.append([date, amount.replace(",", ""), type_, clean_desc, bank_name])

    return transactions


def extract_transactions_apple_card(text):
    bank_name = "Apple Card"
    transactions = []

    # Match lines like: 12/01/2024 DESCRIPTION ... $Amount
    pattern = re.findall(
        r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$\d+\.\d{2}\s+\$(\d+\.\d{2})",
        text,
        re.DOTALL
    )

    for date, desc, amount in pattern:
        clean_desc = " ".join(desc.strip().split())
        type_ = "Purchase"  # Apple Card does not use negative signs for credits in this section
        transactions.append([date, amount, type_, clean_desc, bank_name])

    return transactions



def extract_transactions(text, filename, unknown_files):
    if "Virtual Wallet" in text or "PNC" in text:
        return extract_transactions_pnc(text)
    elif "New Balance" in text and "Payment Due Date" in text:
        return extract_transactions_chase_card(text)
    elif "JPMorgan" in text or "Chase.com" in text:
        return extract_transactions_chase_bank(text)
    elif "Discover" in text and "Activity Period" in text:
        return extract_transactions_discover_card(text)
    elif "American Express" in text and "SkyMiles" in text:
        return extract_transactions_amex(text)
    elif "Apple Card is issued by Goldman Sachs Bank USA" in text:
        return extract_transactions_apple_card(text)
    else:
        print(f"⚠️ Unknown format in: {filename}")
        unknown_files.append(filename)
        return []

def process_all_pdfs(input_folder, output_csv):
    all_transactions = []
    unknown_files = []

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(input_folder, filename)
            print(f"Processing: {file_path}")

            with pdfplumber.open(file_path) as pdf:
                full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

            transactions = extract_transactions(full_text, filename, unknown_files)
            all_transactions.extend(transactions)

    # Save transactions
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Amount", "Type", "Description", "Bank"])
        writer.writerows(all_transactions)

    print(f"\n✅ All transactions saved to: {output_csv}")

    if unknown_files:
        print("\n⚠️ The following files had unknown formats and were skipped:")
        for file in unknown_files:
            print(f" - {file}")

# Example usage
process_all_pdfs("Dataset", "account.csv")
