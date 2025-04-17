import pandas as pd
import re
import json
import os

# Load configuration once
def load_config():
    try:
        with open("creds.json") as creds:
            return json.load(creds)
    except:
        return {
            "CSV_FILE": "Dataset/account.csv",
            "number1": "",
            "number2": "",
            "number3": ""
        }

CONFIG = load_config()

# Define category constants
EXPENSE_CATEGORIES = [
    'Food & Dining', 'Transport', 'Rent', 'Utilities', 
    'Shopping', 'Subscription', 'Vending Machine', 
    'Entertainment', 'Pharmacy', 'Games', 'Tuition', "Other",
    "Cash Withdrawal", "Investments", "Groceries", "Transfer"
]

INCOME_CATEGORIES = ['Income', 'Papa Transfer']
EXCLUDE_CATEGORIES = ["Income", "Papa Transfer", "Internal Transfer"]

# Centralized categorization function
def categorize(description):
    """
    Categorizes a transaction based on its description.
    
    Args:
        description: String containing the transaction description
        
    Returns:
        String representing the category
    """
    desc = description.lower()
    
    # Check for internal transfers first with actual account numbers
    if any(keyword in desc for keyword in [
        f"transfer from {CONFIG.get('number1', '')}", 
        f"transfer from {CONFIG.get('number2', '')}", 
        f"Online Transfer To {CONFIG.get('number3', '')}", 
        "transfer"
    ]):
        return "Internal Transfer"
        
    if any(keyword in desc for keyword in ["meijer", "walmart", "costco", "kroger", "grocery", "aldi", "whole foods"]):
        return "Groceries"
    elif any(keyword in desc for keyword in ["uber eats", "doordash", "grubhub", "restaurant", "dining", "mcdonald's", 
                                           "coffee", "cafe", "chick-fil-a", "raising canes", "chipotle", "aramark", 
                                           "china food", "fortune noodle house", "starbucks", "subway", "the 86", 
                                           "deli", "halal food", "thai express", "adeep india", "drunken", "adriaticos", 
                                           "cheesecake", "united dairy farm", "popeyes"]):
        return "Food & Dining"
    elif any(keyword in desc for keyword in ["uber", "lyft", "ride", "taxi", "masabi_sorta", "american airlines", "masabi"]):
        return "Transport"
    elif any(keyword in desc for keyword in ["netflix", "spotify", "subscription", "apple.com", "openai", "chatgpt", 
                                           "crunchyroll", "chegg"]):
        return "Subscription"
    elif any(keyword in desc for keyword in ["rent", "lease", "apartment", "rebecca", "mclean", "Rebecca "]):
        return "Rent"
    elif any(keyword in desc for keyword in ["zelle to", "venmo", "paypal", "zel to", "zelle payment to", 
                                            "domestic incoming wire fee"]):
        return "Transfer"
    elif any(keyword in desc for keyword in ["salary", "payroll", "deposit", "income", "fedwire", "zelle from", 
                                            "zel from", "desposit", "zelle payment from", "credit", "new checking",
                                            "Daily Cash Deposit"]):
        return "Income"
    elif any(keyword in desc for keyword in ["atm", "cash", "withdrawal"]):
        return "Cash Withdrawal"
    elif any(keyword in desc for keyword in ["amazon", "online", "purchase", "target", "clifton market", "the 86", 
                                           "ravine", "amzn", "prime video", "viv makret", "bana market"]):
        return "Shopping"
    elif any(keyword in desc for keyword in ["dukeenergycorpor", "vzwrlss", "visible"]):
        return "Utilities"
    elif any(keyword in desc for keyword in ["universitycinti", "univ cinti", "university of cincinnati", "uc", 
                                           "univ of cinti"]):
        return "Tuition"
    elif "parlevel texas" in desc:
        return "Vending Machine"
    elif any(keyword in desc for keyword in ["robinhood"]):
        return "Investments"
    elif any(keyword in desc for keyword in ["fandango", "amc"]):
        return "Entertainment"
    elif any(keyword in desc for keyword in ["cvs"]):
        return "Pharmacy"
    elif any(keyword in desc for keyword in ["epic", "steamgames", "playstationnetwork", "nvidia"]):
        return "Games"
    elif any(keyword in desc for keyword in ["Interest"]):
        return "Returns"
    else:
        return "Other"

# Centralized text cleaning
def clean_text(text):
    """
    Cleans text by converting to lowercase and removing special characters.
    
    Args:
        text: String to clean
        
    Returns:
        Cleaned string
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text

# Normalize transaction amounts
def normalize_transaction(row):
    """
    Normalize the transaction amount based on category.
    
    Args:
        row: Pandas Series containing transaction data with at least 'Description' and 'Amount'
        
    Returns:
        Pandas Series with 'Category' and 'Normalized_Amount'
    """
    category = categorize(row['Description'])
    amount = row['Amount']  # This should be positive
    
    # For expense categories, ensure amount is negative
    if category in EXPENSE_CATEGORIES:
        amount = -amount
    
    return pd.Series({
        'Category': category,
        'Normalized_Amount': amount
    })

# Load and preprocess data
def load_data(file_path=None):
    """
    Loads transaction data from CSV and performs standard preprocessing.
    
    Args:
        file_path: Path to CSV file. If None, uses path from config.
        
    Returns:
        Preprocessed DataFrame
    """
    if not file_path:
        file_path = CONFIG.get("CSV_FILE", "Dataset/account.csv")
    
    try:
        df = pd.read_csv(file_path, encoding="ISO-8859-1")
    except:
        df = pd.read_csv("account.csv")  # Fallback to direct file

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Date", "Description"], inplace=True)
    df["Amount"] = df["Amount"].abs()
    
    # Apply categorization and normalization
    result = df.apply(normalize_transaction, axis=1)
    df['Category'] = result['Category']
    df['Normalized_Amount'] = result['Normalized_Amount']
    
    return df

# Extract recipient names from transfer descriptions
def extract_recipients(transfer_descriptions):
    """
    Extracts recipient names from transfer descriptions.
    
    Args:
        transfer_descriptions: List of transfer description strings
        
    Returns:
        List of extracted recipient names
    """
    recipients = []
    for desc in transfer_descriptions:
        desc_lower = desc.lower()
        if "zelle payment to " in desc_lower:
            recipient = desc_lower.split("zelle payment to ")[1].split(" ")[0]
            recipients.append(recipient)
        elif "zelle to " in desc_lower:
            recipient = desc_lower.split("zelle to ")[1].split(" ")[0]
            recipients.append(recipient)
        elif "transfer to " in desc_lower:
            recipient = desc_lower.split("transfer to ")[1].split(" ")[0]
            recipients.append(recipient)
    return recipients