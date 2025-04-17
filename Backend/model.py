import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib
import numpy as np
from sklearn.metrics import confusion_matrix

# Import from utils module instead of defining redundant functions
from utils import categorize, clean_text, load_data, CONFIG

# Load data using the centralized function
df = load_data()

# Apply categorization from utils
df["Category"] = df["Description"].apply(categorize)

# Clean descriptions using the shared function
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
