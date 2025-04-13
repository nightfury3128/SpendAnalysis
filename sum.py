import pandas as pd
import re
import json

# Try to load the config file if available, otherwise use direct path
try:
    with open("creds.json") as creds:
        config = json.load(creds)
        csv_file = config["CSV_FILE"]
        number1 = config["number1"]
        number2 = config["number2"]
        number3=  config["number3"]
except:
    csv_file = "Dataset/account.csv"
    number1 = ""  # Default values if config not found
    number2 = ""

# Load data
try:
    df = pd.read_csv(csv_file, encoding="ISO-8859-1")
except:
    df = pd.read_csv("account.csv")  # Fallback to direct file

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df.dropna(subset=["Date", "Description"], inplace=True)

# After loading data and before normalization, ensure all amounts are positive
df["Amount"] = df["Amount"].abs()

# Enhanced categorization function with internal transfers
def categorize(description):
    desc = description.lower()
    
    # Check for internal transfers first with actual account numbers
    if any(keyword in desc for keyword in [f"transfer from {number1}", f"transfer from {number2}", f"Online Transfer To {number3}", "transfer"]):
        return "Internal Transfer"
    if any(keyword in desc for keyword in ["meijer", "walmart", "costco", "kroger", "grocery", "aldi", "whole foods"]):
        return "Groceries"
    elif any(keyword in desc for keyword in ["uber eats", "doordash", "grubhub", "restaurant", "dining", "mcdonald's", "coffee", "cafe", "chick-fil-a", "raising canes", "chipotle", "aramark", "china food","fortune noodle house", "starbucks","subway", "the 86","deli","halal food","thai express","adeep india","drunken","adriaticos","cheesecake","united dairy farm","popeyes"]):
        return "Food & Dining"
    elif any(keyword in desc for keyword in ["uber", "lyft", "ride", "taxi", "masabi_sorta","american airlines","masabi"]):
        return "Transport"
    elif any(keyword in desc for keyword in ["netflix", "spotify", "subscription", "apple.com", "openai","chatgpt", "crunchyroll","chegg"]):
        return "Subscription"
    elif any(keyword in desc for keyword in ["rent", "lease", "apartment", "rebecca", "mclean", "Rebecca "]):
        return "Rent"
    elif any(keyword in desc for keyword in ["zelle to", "venmo", "paypal", "zel to", "zelle payment to", "domestic incoming wire fee"]):
        return "Transfer"
    elif any(keyword in desc for keyword in ["salary", "payroll", "deposit", "income","fedwire", "zelle from", "zel from", "desposit", "zelle payment from","credit", "new checking","Daily Cash Deposit"]):
        return "Income"
    elif any(keyword in desc for keyword in ["atm", "cash", "withdrawal"]):
        return "Cash Withdrawal"
    elif any(keyword in desc for keyword in ["amazon", "online", "purchase", "target", "clifton market", "the 86", "ravine", "amzn", "prime video", "viv makret", "bana market"]):
        return "Shopping"
    elif any(keyword in desc for keyword in ["dukeenergycorpor", "vzwrlss","visible"]):
        return "Utilities"
    elif any(keyword in desc for keyword in ["universitycinti", "univ cinti", "university of cincinnati", "uc", "univ of cinti"]):
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

# Process transactions by their Type field
def normalize_transaction(row):
    """Normalize the transaction amount based on category and transaction type"""
    category = categorize(row['Description'])
    amount = row['Amount']  # Now this will always be positive
    
    # Define expense categories that should always be negative
    expense_categories = [
        'Food & Dining', 'Transport', 'Rent', 'Utilities', 
        'Shopping', 'Subscription', 'Vending Machine', 
        'Entertainment', 'Pharmacy', 'Games', 'Tuition', "Other",
        "Cash Withdrawal", "Investments", "Groceries", "Transfer"
    ]
    
    # Define income categories that should always be positive
    income_categories = ['Income']
    
    # For expense categories, ensure amount is negative
    if category in expense_categories:
        amount = -amount
    
    # Income categories remain positive by default
    
    return pd.Series({
        'Category': category,
        'Normalized_Amount': amount
    })

# Apply categorization and normalization
result = df.apply(normalize_transaction, axis=1)
df['Category'] = result['Category']
df['Normalized_Amount'] = result['Normalized_Amount']

# Calculate total amount by category using the normalized amounts
category_totals = df.groupby('Category')['Normalized_Amount'].sum().sort_values()


for category, total in category_totals.items():
    print(f"{category:<20} ${total:>14,.2f}")

orig_totals = df.groupby('Category')['Amount'].sum().sort_values()
for category, total in orig_totals.items():
    print(f"{category:<20} ${total:>14,.2f}")


internal_transfers = df[df['Category'] == 'Internal Transfer'].sort_values('Date')
if len(internal_transfers) > 0:
    for _, row in internal_transfers.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d')
        print(f"{date_str:<12} ${row['Amount']:>9,.2f} {row['Type']:<10} {row['Description'][:50]}")
    
    # Calculate net effect of internal transfers
    net_internal = internal_transfers['Amount'].sum()
    print(f"\nNet effect of internal transfers: ${net_internal:,.2f}")
    print(f"Total internal transfers: {len(internal_transfers)} transactions")
else:
    print("No internal transfers found")


other_transactions = df[df['Category'] == 'Other'].sort_values('Date')
for _, row in other_transactions.iterrows():
    date_str = row['Date'].strftime('%Y-%m-%d')
    print(f"{date_str:<12} ${row['Amount']:>9,.2f} {row['Type']:<10} {row['Description'][:50]}")



transfer_transactions = df[df['Category'] == 'Transfer'].sort_values('Date')
if len(transfer_transactions) > 0:
    for _, row in transfer_transactions.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d')
        print(f"{date_str:<12} ${row['Amount']:>9,.2f} {row['Type']:<10} {row['Description'][:50]}")

    
    # Show the top recipients of transfers (extract names from descriptions)
    try:
        # Extract potential recipient names from Zelle transfers
        recipients = []
        for desc in transfer_transactions['Description']:
            desc_lower = desc.lower()
            if "zelle payment to " in desc_lower:
                # Try to extract the recipient name
                recipient = desc_lower.split("zelle payment to ")[1].split(" ")[0]
                recipients.append(recipient)
            elif "zelle to " in desc_lower:
                recipient = desc_lower.split("zelle to ")[1].split(" ")[0]
                recipients.append(recipient)
            elif "transfer to " in desc_lower:
                recipient = desc_lower.split("transfer to ")[1].split(" ")[0]
                recipients.append(recipient)
        
        # Count occurrences of each recipient
        from collections import Counter
        recipient_counts = Counter(recipients)
        
        if recipient_counts:
            print("\nTop transfer recipients:")
            for recipient, count in recipient_counts.most_common(5):
                print(f"- {recipient.title()}: {count} transfers")
    except:
        pass  # Skip this analysis if there's any error
else:
    print("No transfer transactions found")

# Calculate true savings (income minus expenses, excluding internal transfers)
total_income = df[df['Category'] == 'Income']['Normalized_Amount'].sum()
total_expenses = df[(df['Category'] != 'Income') & (df['Category'] != 'Internal Transfer')]['Normalized_Amount'].sum()
savings = total_income + total_expenses  # Expenses are negative, so we add


