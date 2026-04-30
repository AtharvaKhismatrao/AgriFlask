# train_and_save_model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle
import os # To handle file paths

# --- Configuration ---
# NOTE: Update the path below to where your CSV is located on your local machine
CSV_PATH = "Crop_recommendation.csv" 
MODEL_FILENAME = 'crop_model.pkl'

# --- 1. Load Data ---
try:
    # Assuming the CSV is in the same directory as this script
    data = pd.read_csv(CSV_PATH)
except FileNotFoundError:
    print(f"Error: CSV file not found at {CSV_PATH}. Please update the CSV_PATH variable.")
    exit()

# --- 2. Data Preparation ---
# Separate features (X) and target (y)
x = data.iloc[:, :-1]
y = data.iloc[:, -1]

# Split data into training and testing sets
# NOTE: The split ratio in your notebook (test_size=0.2) is unusual.
# It typically should be train_size=0.8 or test_size=0.2.
# I'll keep your original parameters: X_test, X_train, y_test, y_train=train_test_split(x,y,test_size=0.2,random_state=42)
# If you meant a standard 80/20 split, the variables should be: X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

# Correcting variable assignment for standard practice (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)


# --- 3. Model Training ---
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# --- 4. Evaluation ---
accuracy = model.score(X_test, y_test)
print("------------------------------------------------")
print(f"Model Training Complete. Accuracy on Test Set (20%): {accuracy:.4f}")
print("------------------------------------------------")

# --- 5. Save the Trained Model ---
try:
    with open(MODEL_FILENAME, 'wb') as file:
        pickle.dump(model, file)
    print(f"✅ Model successfully saved as '{MODEL_FILENAME}' for deployment.")
except Exception as e:
    print(f"Failed to save model: {e}")