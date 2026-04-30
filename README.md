#  AGRIFLASK – Smart Crop Prediction System

AGRIFLASK is a Flask-based intelligent web application designed to help users identify the most suitable crop for cultivation using Machine Learning. The system predicts crops based on environmental and soil parameters while also providing a role-based user experience for Farmers, Agricultural Analysts, and Students.

This project combines **Machine Learning, Web Development, Database Management, and Role-Based Authentication** into one practical agriculture-focused solution.

---

##  Features

###  Crop Prediction using Machine Learning
Predicts the best crop based on:

- Nitrogen (N)
- Phosphorus (P)
- Potassium (K)
- Temperature
- Humidity
- pH Value
- Rainfall

###  User Authentication System

- User Registration
- Login / Logout
- MySQL Database Credential Storage
- Unique User ID Validation
- Session Handling


###  Dynamic Role Switching

Logged-in users can switch roles and explore different dashboards.

###  Multilingual Support

Supports multiple languages:

- English
- Hindi
- Tamil

---

##  Technologies Used

### Backend

- Python
- Flask
- MySQL
- Flask Sessions

### Frontend

- HTML
- CSS
- Bootstrap
- JavaScript

### Machine Learning

- Scikit-learn
- Random Forest Classifier
- Pandas
- NumPy

---

## 📂 Project Structure

```bash
AGRIFLASK/
│── static/
│   ├── css/
│   ├── images/
│
│── templates/
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── farmer_index.html
│   ├── analyst_index.html
│   ├── student_index.html
│
│── main.py
│── main2.py
│── model.py
│── crop_model.pkl
│── Crop_recommendation.csv
│── README.md
