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

    if any(keyword in desc for keyword in ["meijer", "walmart", "costco", "kroger", "grocery", "aldi", "whole foods"]):
        return "Groceries"
    elif any(keyword in desc for keyword in ["uber eats", "doordash", "grubhub", "restaurant", "dining", "mcdonalds", "coffee", "cafe", "chick-fil-a", "raising canes", "chipotle", "aramark", "china food","fortune noodle house", "starbucks","subway", "the 86","deli","halal food","thai express","adeep india","drunken","adriaticos","cheesecake","united dairy farm","popeyes"]):
        return "Food & Dining"
    elif any(keyword in desc for keyword in ["uber", "lyft", "ride", "taxi", "masabi_sorta","american airlines"]):
        return "Transport"
    elif any(keyword in desc for keyword in ["netflix", "spotify", "subscription", "apple.com", "openai","chatgpt"]):
        return "Subscription"
    elif any(keyword in desc for keyword in ["rent", "lease", "apartment", "rebecca", "mclean", "Rebecca "] ):
        print(f"Rent detected in: {desc} of amount {df.loc[df['Description'] == description, 'Amount'].values[0]}")
        return "Rent"
    elif any(keyword in desc for keyword in ["zelle", "venmo", "paypal", "transfer"]):
        return "Transfer"
    elif any(keyword in desc for keyword in ["salary", "payroll", "deposit", "income"]):
        return "Income"
    elif any(keyword in desc for keyword in ["cash deposit"]):
        return "Cash Deposit"
    elif any(keyword in desc for keyword in ["atm", "cash", "withdrawal"]):
        return "Cash Withdrawal"
    elif any(keyword in desc for keyword in ["amazon", "online", "purchase", "target", "clifton market", "the 86", "ravine", "amzn", "prime video", "viv makret", "bana market"]):
        return "Shopping"
    elif any(keyword in desc for keyword in ["fedwire", "domestic incoming wire fee"]):
        return "Papa Transfer"
    elif any(keyword in desc for keyword in ["dukeenergycorpor", "vzwrlss","visible"]):
        return "Utilities"
    elif any(keyword in desc for keyword in ["universitycinti", "univ cinti", "university of cincinnati", "uc", "univ of cinti"]):
        return "Tuition"
    elif "parlevel texas" in desc:
        return "Vending Machine"
    elif any(keyword in desc for keyword in ["robinhood"]):
        return "Investments"
    elif any(keyword in desc for keyword in ["fandango"]):
        return "Entertainment"
    elif any(keyword in desc for keyword in ["cvs"]):
        return "Pharmacy"
    elif any(keyword in desc for keyword in ["epic", "steamgames", "playstationnetwork", "nvidia"]):
        print(f"Games detected in: {desc} of amount {df.loc[df['Description'] == description, 'Amount'].values[0]}")
        return "Games"
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

# Train/test split
X = df["Cleaned_Description"]
y = df["Category"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42,)

# TF-IDF Vectorization
vectorizer = TfidfVectorizer()
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Train model
model = LogisticRegression(max_iter=1000)
model.fit(X_train_vec, y_train)

# Evaluate model
y_pred = model.predict(X_test_vec)
print("Classification Report:\n", classification_report(y_test, y_pred))
print("Total categorized as Rent:", (df["Category"] == "Rent").sum())
print("Rent in training set:", sum(y_train == "Rent"))
print("Rent in test set:", sum(y_test == "Rent"))
print ("Total categorized as Games:", (df["Category"] == "Games").sum())
print("Games in training set:", sum(y_train == "Games"))
print("Games in test set:", sum(y_test == "Games"))
# Save the model and vectorizer
joblib.dump(model, "category_classifier_model.pkl")
joblib.dump(vectorizer, "tfidf_vectorizer.pkl")
