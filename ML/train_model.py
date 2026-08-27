import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle

# Load dataset
data = pd.read_csv("ML/dataset.csv")

# EXACT 6 input features
features = [
    "python_skill",
    "java_skill",
    "sql_skill",
    "tenth_percentage",
    "twelfth_percentage",
    "graduation_percentage"
]

X = data[features]
y = data["career"]

# Encode career
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y_encoded,
    test_size=0.2,
    random_state=42
)

# Model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

print("Model trained successfully!")
print("Number of input features:", X.shape[1])
print("Model Accuracy:", model.score(X_test, y_test))

# Save
with open("ML/career_model.pkl", "wb") as file:
    pickle.dump((model, label_encoder), file)

print("career_model.pkl created successfully!")