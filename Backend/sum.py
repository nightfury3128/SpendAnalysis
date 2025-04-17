import pandas as pd
import re
from collections import Counter

# Import shared functionality from utils module
from utils import (
    load_data, 
    categorize, 
    normalize_transaction, 
    extract_recipients, 
    CONFIG,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES
)

# Load preprocessed data using the utility function
df = load_data()

# Calculate total amount by category using the normalized amounts
category_totals = df.groupby('Category')['Normalized_Amount'].sum().sort_values()

# Print category totals
for category, total in category_totals.items():
    print(f"{category:<20} ${total:>14,.2f}")

# Show original totals for comparison/verification
orig_totals = df.groupby('Category')['Amount'].sum().sort_values()
for category, total in orig_totals.items():
    print(f"{category:<20} ${total:>14,.2f}")

# Display internal transfers
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

# Display transactions categorized as "Other"
other_transactions = df[df['Category'] == 'Other'].sort_values('Date')
for _, row in other_transactions.iterrows():
    date_str = row['Date'].strftime('%Y-%m-%d')
    print(f"{date_str:<12} ${row['Amount']:>9,.2f} {row['Type']:<10} {row['Description'][:50]}")

# Display transfer transactions with recipient analysis
transfer_transactions = df[df['Category'] == 'Transfer'].sort_values('Date')
if len(transfer_transactions) > 0:
    for _, row in transfer_transactions.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d')
        print(f"{date_str:<12} ${row['Amount']:>9,.2f} {row['Type']:<10} {row['Description'][:50]}")

    # Show the top recipients of transfers (extract names from descriptions)
    try:
        # Use the extract_recipients utility function
        recipients = extract_recipients(transfer_transactions['Description'])
        
        # Count occurrences of each recipient
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

print(f"\nTotal Income: ${total_income:,.2f}")
print(f"Total Expenses: ${abs(total_expenses):,.2f}")
print(f"Total Savings: ${savings:,.2f}")
print(f"Savings Rate: {(savings/total_income*100 if total_income > 0 else 0):,.2f}%")


