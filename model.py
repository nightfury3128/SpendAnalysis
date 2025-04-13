import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib
import json 

with open ("creds.json") as creds: 
    config = json.load(creds)
# Load data
df = pd.read_csv(config["CSV_FILE"], encoding="ISO-8859-1")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df.dropna(subset=["Date", "Description"], inplace=True)

# Enhanced categorization function
def categorize(description):
    desc = description.lower()
    
    # Try to load config with account numbers if available
    try:
        with open ("creds.json") as creds: 
            config = json.load(creds)
            number1 = config.get("number1", "")
            number2 = config.get("number2", "")
            number3 = config.get("number3", "")
            
        # Check for internal transfers first with actual account numbers
        if any(keyword in desc for keyword in [f"transfer from {number1}", f"transfer from {number2}", 
                                              f"Online Transfer To {number3}", "transfer"]):
            return "Internal Transfer"
    except:
        pass  # Continue with other categories if config not found
        
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
        print(f"Rent detected in: {desc} of amount {df.loc[df['Description'] == description, 'Amount'].values[0]}")
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
        print(f"Games detected in: {desc} of amount {df.loc[df['Description'] == description, 'Amount'].values[0]}")
        return "Games"
    elif any(keyword in desc for keyword in ["Interest"]):
        return "Returns"
    else:
        return "Other"

# Apply categorization
df["Category"] = df["Description"].apply(categorize)

# Clean descriptions
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text

df["Cleaned_Description"] = df["Description"].apply(clean_text)

# Train/test split with stratification to ensure all categories have examples
X = df["Cleaned_Description"]
y = df["Category"]

# First, check which categories have too few examples
category_counts = df["Category"].value_counts()
print("\nCategory distribution:")
for category, count in category_counts.items():
    print(f"{category}: {count}")

# Use stratified sampling for categories with sufficient examples
try:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
except ValueError:
    # If stratification fails due to too few examples in some classes, fall back to regular split
    print("Warning: Stratified sampling failed, using regular split instead")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
# Print class distribution in train and test sets
print("\nTrain set distribution:")
train_dist = pd.Series(y_train).value_counts()
for category in category_counts.index:
    count = train_dist.get(category, 0)
    print(f"{category}: {count}")
    
print("\nTest set distribution:")
test_dist = pd.Series(y_test).value_counts()
for category in category_counts.index:
    count = test_dist.get(category, 0)
    print(f"{category}: {count}")

# Identify categories with too few examples for reliable classification
min_examples = 5
low_count_categories = category_counts[category_counts < min_examples].index.tolist()
if low_count_categories:
    print(f"\nWarning: The following categories have fewer than {min_examples} examples:")
    for category in low_count_categories:
        print(f"- {category}: {category_counts[category]} examples")
    print("Consider adding more examples or merging these categories.")

# TF-IDF Vectorization
vectorizer = TfidfVectorizer()
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Train model with class weights to handle imbalanced categories
model = LogisticRegression(max_iter=1000, class_weight='balanced')
model.fit(X_train_vec, y_train)

# Evaluate model
y_pred = model.predict(X_test_vec)
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# Print confusion matrix for categories with poor performance
from sklearn.metrics import confusion_matrix
import numpy as np

# Get unique classes in sorted order
classes = np.unique(np.concatenate([y_test, y_pred]))

# Generate confusion matrix
cm = confusion_matrix(y_test, y_pred, labels=classes)

# Print confusion matrix for problematic categories
print("\nConfusion matrix for problematic categories:")
problem_categories = []
for i, category in enumerate(classes):
    correct = cm[i, i]
    total = np.sum(cm[i, :])
    if total > 0 and correct / total < 0.5:  # Less than 50% accuracy
        problem_categories.append(i)

if problem_categories:
    # Extract relevant rows and columns
    sub_cm = cm[problem_categories, :]
    sub_classes = [classes[i] for i in problem_categories]
    
    print("\nActual vs Predicted")
    print("Actual categories:", sub_classes)
    print(sub_cm)
    print("Predicted categories:", list(classes))
else:
    print("No major issues found in category predictions.")

# Save the model and vectorizer
joblib.dump(model, "category_classifier_model.pkl")
joblib.dump(vectorizer, "tfidf_vectorizer.pkl")
