from collections import defaultdict
import csv
import os
from statistics import mean, median

from flask import Flask, render_template, request, redirect, session, url_for
import numpy as np
import pandas as pd
import pickle
import mysql.connector
from mysql.connector import Error as MySQLError
from werkzeug.security import check_password_hash, generate_password_hash

def load_local_env(env_path: str = ".env") -> None:
    """Load simple KEY=VALUE pairs from a local .env file into process env."""
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# Load environment variables from local .env when available.
load_local_env()

app = Flask(__name__)
app.secret_key = "agriflask-session-key"

LANGUAGES = {
    "en": {"name": "English"},
    "hi": {"name": "Hindi"},
    "ta": {"name": "Tamil"},
}

TRANSLATIONS = {
    "en": {
        "nav.home": "Home",
        "nav.about": "About",
        "nav.contact": "Contact us",
        "nav.login": "Login",
        "nav.language": "Language",
        "nav.account.edit": "Change Role",
        "nav.account.logout": "Logout",
        "home.title": "HarvestIQ",
        "home.subtitle": "Smart Crop Prediction System",
        "home.predict": "Prediction",
        "home.about_title": "ABOUT US",
        "home.about_text_1": "HarvestIQ is a smart crop prediction system designed to assist different stakeholders in agriculture by providing data-driven crop recommendations. The system uses machine learning techniques to analyze soil and environmental parameters such as nitrogen, phosphorus, potassium, temperature, humidity, pH level, and rainfall to predict the most suitable crop for cultivation.",
        "home.about_text_2": "By combining machine learning, data analysis, and an intuitive user interface, HarvestIQ aims to bridge the gap between agricultural data and real-world applications, contributing toward smarter and more sustainable farming practices.",
        "home.contact_title": "Contact Us",
        "login.title": "HarvestIQ | Login",
        "login.brand": "HarvestIQ",
        "login.subtitle": "Smart Crop Prediction System",
        "login.welcome": "Welcome",
        "login.manage": "Manage Account",
        "login.login_prompt": "Login to your account",
        "login.manage_prompt": "Update your ID, password, or role",
        "login.id": "ID",
        "login.password": "Password",
        "login.role": "Role",
        "login.forgot": "Forgot Password",
        "login.submit": "Login",
        "login.save": "Save",
        "login.role_farmer": "Farmer",
        "login.role_analyst": "Agricultural Analyst",
        "login.role_student": "Student",
        "login.placeholder_role": "Select your role",
        "login.status": "",
        "farmer.title": "HarvestIQ",
        "farmer.subtitle": "Qualitative field inputs converted to model values",
        "farmer.submit": "Predict Crop (Farmer Mode)",
        "analyst.eyebrow": "Agricultural Analyst Workspace",
        "analyst.title": "High-precision crop prediction with historical context.",
        "analyst.subtitle": "Enter the measured field values directly. This analyst view keeps the prediction logic strict, then explains the result with historical crop statistics, feature importance, and a radar comparison against the closest crop profiles.",
        "analyst.submit": "Run Analyst Prediction",
        "analyst.inputs": "Inputs",
        "analyst.alternatives": "Alternatives",
        "analyst.model": "Model",
        "analyst.result_placeholder": "Run a prediction to see the crop recommendation, the historical summary, the feature importance breakdown, and the radar chart comparison.",
        "analyst.context": "Context warnings",
        "analyst.summary": "Historical summary",
        "analyst.reasoning": "Why the model chose this crop",
        "analyst.importance": "Feature importance",
        "analyst.radar": "Radar comparison",
        "analyst.closest": "Closest alternatives",
        # Farmer form labels
        "farmer.soil_texture": "Soil texture",
        "farmer.soil_texture_sandy": "Sandy",
        "farmer.soil_texture_loamy": "Loamy",
        "farmer.soil_texture_clayey": "Clayey",
        "farmer.soil_texture_silty": "Silty",
        "farmer.soil_fertility": "Soil fertility observation",
        "farmer.soil_fertility_low": "Low",
        "farmer.soil_fertility_medium": "Medium",
        "farmer.soil_fertility_high": "High",
        "farmer.soil_appearance": "Soil appearance",
        "farmer.soil_appearance_normal": "Normal-looking soil",
        "farmer.soil_appearance_white_crust": "White crust / salty surface",
        "farmer.soil_appearance_very_dark": "Very dark / organic-looking soil",
        "farmer.soil_appearance_sticky_clay": "Sticky clay / water-retaining soil",
        "farmer.soil_appearance_not_sure": "Not sure",
        "farmer.air_humidity": "Air humidity feel",
        "farmer.humidity_very_dry": "Very dry",
        "farmer.humidity_dry": "Dry",
        "farmer.humidity_comfortable": "Comfortable",
        "farmer.humidity_humid": "Humid",
        "farmer.humidity_very_humid": "Very humid",
        "farmer.rainfall_pattern": "Rainfall in last 30 days",
        "farmer.rainfall_very_low": "Very low rain",
        "farmer.rainfall_light": "Light rain",
        "farmer.rainfall_moderate": "Moderate rain",
        "farmer.rainfall_heavy": "Heavy rain",
        "farmer.rainfall_very_heavy": "Very heavy rain",
        "farmer.temperature_feel": "Temperature feel",
        "farmer.temperature_cool": "Cool",
        "farmer.temperature_mild": "Mild",
        "farmer.temperature_warm": "Warm",
        "farmer.temperature_hot": "Hot",
        # Analyst form labels and hints
        "analyst.nitrogen": "Nitrogen (N)",
        "analyst.nitrogen_hint": "Expected range: 10 to 120 kg/ha",
        "analyst.phosphorus": "Phosphorus (P)",
        "analyst.phosphorus_hint": "Expected range: 10 to 110 kg/ha",
        "analyst.potassium": "Potassium (K)",
        "analyst.potassium_hint": "Expected range: 10 to 180 kg/ha",
        "analyst.temperature": "Temperature (°C)",
        "analyst.temperature_hint": "Expected range: 8 to 42 °C",
        "analyst.humidity": "Humidity (%)",
        "analyst.humidity_hint": "Expected range: 20 to 95%",
        "analyst.ph": "pH Level",
        "analyst.ph_hint": "Expected range: 4.5 to 8.5",
        "analyst.rainfall": "Rainfall (mm)",
        "analyst.rainfall_hint": "Expected range: 20 to 300 mm",
        "analyst.run_prediction": "Run Analyst Prediction",
        "analyst.what_view_title": "What this view gives the analyst",
        "analyst.what_view_text": "The model output is not just the predicted crop. It also shows which historical crop profile the input most resembles, which inputs push the prediction, and how close the nearest alternatives are.",
        "analyst.badge_prediction": "Prediction + confidence",
        "analyst.badge_summary": "Historical crop summary",
        "analyst.badge_importance": "Feature importance",
        "analyst.badge_radar": "Radar comparison",
        "analyst.table_feature": "Feature",
        "analyst.table_input": "Input",
        "analyst.table_mean": "Crop mean",
        "analyst.table_median": "Median",
        "analyst.table_range": "Typical range",
        "analyst.table_fit": "Fit",
        "analyst.table_placeholder": "Historical statistics will appear here after a prediction is made.",
        "analyst.reasoning_placeholder": "The explanation points are generated after the prediction runs.",
        "analyst.radar_description": "The radar chart compares the user's input against the predicted crop's historical profile and the nearest alternative crops.",
        "analyst.alternatives_placeholder": "Alternative crops will be listed after the model produces a result.",
        "student.eyebrow": "Student analysis view",
        "student.title": "Crop prediction with explanation",
        "student.subtitle": "Use the same numeric field measurements as the analyst view, but see only the predicted crop, the next two alternatives, and the main feature driving the result.",
        "student.submit": "Run Student Prediction",
        "student.panel_title": "Prediction summary",
        "student.panel_placeholder": "Run a prediction to see the crop ranking and explanation.",
        "student.top_crops": "Top 3 crops",
        "student.reasoning_title": "Why these crops",
        "student.strongest_title": "Most influential field",
        "student.inputs": "Inputs",
    },
    "hi": {
        "nav.home": "होम",
        "nav.about": "हमारे बारे में",
        "nav.contact": "संपर्क करें",
        "nav.login": "लॉगिन",
        "nav.language": "भाषा",
        "nav.account.edit": "भूमिका बदलें",
        "nav.account.logout": "लॉगआउट",
        "home.title": "HarvestIQ",
        "home.subtitle": "स्मार्ट फसल भविष्यवाणी प्रणाली",
        "home.predict": "भविष्यवाणी",
        "home.about_title": "हमारे बारे में",
        "home.about_text_1": "HarvestIQ एक स्मार्ट फसल भविष्यवाणी प्रणाली है जो कृषि में अलग-अलग उपयोगकर्ताओं को डेटा-आधारित फसल सुझाव देने के लिए बनाई गई है। यह सिस्टम नाइट्रोजन, फॉस्फोरस, पोटैशियम, तापमान, आर्द्रता, pH स्तर और वर्षा जैसे मानकों का विश्लेषण करके सबसे उपयुक्त फसल की भविष्यवाणी करता है।",
        "home.about_text_2": "मशीन लर्निंग, डेटा विश्लेषण और आसान इंटरफ़ेस को जोड़कर HarvestIQ कृषि डेटा और वास्तविक जीवन के उपयोग के बीच की दूरी कम करने का प्रयास करता है।",
        "home.contact_title": "संपर्क करें",
        "login.title": "HarvestIQ | लॉगिन",
        "login.brand": "HarvestIQ",
        "login.subtitle": "स्मार्ट फसल भविष्यवाणी प्रणाली",
        "login.welcome": "स्वागत है",
        "login.manage": "खाता प्रबंधन",
        "login.login_prompt": "अपने खाते में लॉगिन करें",
        "login.manage_prompt": "अपनी आईडी, पासवर्ड या भूमिका बदलें",
        "login.id": "आईडी",
        "login.password": "पासवर्ड",
        "login.role": "भूमिका",
        "login.forgot": "पासवर्ड भूल गए",
        "login.submit": "लॉगिन",
        "login.save": "सहेजें",
        "login.role_farmer": "किसान",
        "login.role_analyst": "कृषि विश्लेषक",
        "login.role_student": "छात्र",
        "login.placeholder_role": "अपनी भूमिका चुनें",
        "farmer.title": "HarvestIQ",
        "farmer.subtitle": "किसानों के लिए सरल इनपुट को मॉडल मानों में बदला जाता है",
        "farmer.submit": "फसल बताएं (किसान मोड)",
        "analyst.eyebrow": "कृषि विश्लेषक कार्यक्षेत्र",
        "analyst.title": "इतिहास आधारित उच्च-शुद्धता फसल भविष्यवाणी।",
        "analyst.subtitle": "यहां आप सीधे मापे हुए मान दर्ज करते हैं। यह दृश्य prediction, historical summary, feature importance और radar तुलना दिखाता है।",
        "analyst.submit": "विश्लेषण शुरू करें",
        "analyst.inputs": "इनपुट",
        "analyst.alternatives": "विकल्प",
        "analyst.model": "मॉडल",
        "analyst.result_placeholder": "भविष्यवाणी करने पर summary, importance और radar chart यहां दिखाई देंगे।",
        "analyst.context": "स्थिति चेतावनियाँ",
        "analyst.summary": "ऐतिहासिक सारांश",
        "analyst.reasoning": "मॉडल ने यह फसल क्यों चुनी",
        "analyst.importance": "फीचर महत्व",
        "analyst.radar": "रेडार तुलना",
        "analyst.closest": "निकटतम विकल्प",
        # Farmer form labels
        "farmer.soil_texture": "मृदा की संरचना",
        "farmer.soil_texture_sandy": "बलुई",
        "farmer.soil_texture_loamy": "दोमट",
        "farmer.soil_texture_clayey": "चिकनी",
        "farmer.soil_texture_silty": "गाद युक्त",
        "farmer.soil_fertility": "मृदा उर्वरता अवलोकन",
        "farmer.soil_fertility_low": "कम",
        "farmer.soil_fertility_medium": "मध्यम",
        "farmer.soil_fertility_high": "उच्च",
        "farmer.soil_appearance": "मृदा की उपस्थिति",
        "farmer.soil_appearance_normal": "सामान्य दिखने वाली मिट्टी",
        "farmer.soil_appearance_white_crust": "सफेद परत / नमकीन सतह",
        "farmer.soil_appearance_very_dark": "बहुत गहरी / जैविक दिखने वाली मिट्टी",
        "farmer.soil_appearance_sticky_clay": "चिपचिपी मिट्टी / पानी रोकने वाली मिट्टी",
        "farmer.soil_appearance_not_sure": "निश्चित नहीं",
        "farmer.air_humidity": "वायु आर्द्रता महसूस करें",
        "farmer.humidity_very_dry": "बहुत सूखा",
        "farmer.humidity_dry": "सूखा",
        "farmer.humidity_comfortable": "आरामदायक",
        "farmer.humidity_humid": "आर्द्र",
        "farmer.humidity_very_humid": "बहुत आर्द्र",
        "farmer.rainfall_pattern": "पिछले 30 दिनों में वर्षा",
        "farmer.rainfall_very_low": "बहुत कम वर्षा",
        "farmer.rainfall_light": "हल्की वर्षा",
        "farmer.rainfall_moderate": "सामान्य वर्षा",
        "farmer.rainfall_heavy": "भारी वर्षा",
        "farmer.rainfall_very_heavy": "बहुत भारी वर्षा",
        "farmer.temperature_feel": "तापमान महसूस करें",
        "farmer.temperature_cool": "ठंडा",
        "farmer.temperature_mild": "हल्का",
        "farmer.temperature_warm": "गर्म",
        "farmer.temperature_hot": "बहुत गर्म",
        # Analyst form labels and hints
        "analyst.nitrogen": "नाइट्रोजन (N)",
        "analyst.nitrogen_hint": "अपेक्षित रेंज: 10 से 120 kg/ha",
        "analyst.phosphorus": "फॉस्फोरस (P)",
        "analyst.phosphorus_hint": "अपेक्षित रेंज: 10 से 110 kg/ha",
        "analyst.potassium": "पोटैशियम (K)",
        "analyst.potassium_hint": "अपेक्षित रेंज: 10 से 180 kg/ha",
        "analyst.temperature": "तापमान (°C)",
        "analyst.temperature_hint": "अपेक्षित रेंज: 8 से 42 °C",
        "analyst.humidity": "आर्द्रता (%)",
        "analyst.humidity_hint": "अपेक्षित रेंज: 20 से 95%",
        "analyst.ph": "pH स्तर",
        "analyst.ph_hint": "अपेक्षित रेंज: 4.5 से 8.5",
        "analyst.rainfall": "वर्षा (mm)",
        "analyst.rainfall_hint": "अपेक्षित रेंज: 20 से 300 mm",
        "analyst.run_prediction": "विश्लेषण शुरू करें",
        "analyst.what_view_title": "यह दृश्य विश्लेषक को क्या देता है",
        "analyst.what_view_text": "मॉडल का आउटपुट केवल अनुमानित फसल नहीं है। यह यह भी दिखाता है कि ऐतिहासिक फसल प्रोफ़ाइल इनपुट से कैसे मिलता है, कौन से इनपुट prediction को प्रभावित करते हैं, और निकटतम विकल्प कितने करीब हैं।",
        "analyst.badge_prediction": "भविष्यवाणी + विश्वास",
        "analyst.badge_summary": "ऐतिहासिक फसल सारांश",
        "analyst.badge_importance": "फीचर महत्व",
        "analyst.badge_radar": "रेडार तुलना",
        "analyst.table_feature": "फीचर",
        "analyst.table_input": "इनपुट",
        "analyst.table_mean": "फसल माध्य",
        "analyst.table_median": "माध्यिका",
        "analyst.table_range": "विशिष्ट रेंज",
        "analyst.table_fit": "फिट",
        "analyst.table_placeholder": "एक भविष्यवाणी करने के बाद ऐतिहासिक आंकड़े यहां दिखाई देंगे।",
        "analyst.reasoning_placeholder": "व्याख्या बिंदु भविष्यवाणी के चलने के बाद उत्पन्न होते हैं।",
        "analyst.radar_description": "रेडार चार्ट उपयोगकर्ता के इनपुट की तुलना अनुमानित फसल की ऐतिहासिक प्रोफ़ाइल और निकटतम वैकल्पिक फसलों से करता है।",
        "analyst.alternatives_placeholder": "मॉडल परिणाम उत्पन्न करने के बाद वैकल्पिक फसलें यहां सूचीबद्ध होंगी।",
        "student.eyebrow": "छात्र विश्लेषण दृश्य",
        "student.title": "व्याख्या के साथ फसल भविष्यवाणी",
        "student.subtitle": "विश्लेषक दृश्य जैसे ही 7 संख्यात्मक मान दर्ज करें, लेकिन केवल अनुमानित फसल, अगले दो विकल्प, और सबसे प्रभावी फीचर देखें।",
        "student.submit": "छात्र भविष्यवाणी चलाएँ",
        "student.panel_title": "भविष्यवाणी सारांश",
        "student.panel_placeholder": "फसल क्रम और व्याख्या देखने के लिए भविष्यवाणी चलाएँ।",
        "student.top_crops": "शीर्ष 3 फसलें",
        "student.reasoning_title": "ये फसलें क्यों चुनी गईं",
        "student.strongest_title": "सबसे प्रभावी क्षेत्र",
        "student.inputs": "इनपुट",
    },
    "ta": {
        "nav.home": "முகப்பு",
        "nav.about": "எங்களை பற்றி",
        "nav.contact": "தொடர்பு கொள்ள",
        "nav.login": "உள்நுழை",
        "nav.language": "மொழி",
        "nav.account.edit": "பங்கை மாற்று",
        "nav.account.logout": "வெளியேறு",
        "home.title": "HarvestIQ",
        "home.subtitle": "ஸ்மார்ட் பயிர் கணிப்பு அமைப்பு",
        "home.predict": "கணிப்பு",
        "home.about_title": "எங்களை பற்றி",
        "home.about_text_1": "HarvestIQ என்பது வேளாண்மை பயனாளர்களுக்கு தரவின் அடிப்படையில் பயிர் பரிந்துரைகளை வழங்க உருவாக்கப்பட்ட ஒரு ஸ்மார்ட் கணிப்பு அமைப்பு. இது நைட்ரஜன், பாஸ்பரஸ், பொட்டாசியம், வெப்பநிலை, ஈரப்பதம், pH மற்றும் மழைப்பொழிவு போன்ற அளவுகளை ஆய்வு செய்து பொருத்தமான பயிரை கணிக்கிறது.",
        "home.about_text_2": "யந்திரக் கற்றல், தரவு பகுப்பாய்வு மற்றும் எளிய பயனர் இடைமுகத்தை இணைப்பதன் மூலம் HarvestIQ வேளாண்மை தரவையும் நடைமுறை பயன்பாட்டையும் இணைக்க முயல்கிறது.",
        "home.contact_title": "தொடர்பு கொள்ள",
        "login.title": "HarvestIQ | உள்நுழை",
        "login.brand": "HarvestIQ",
        "login.subtitle": "ஸ்மார்ட் பயிர் கணிப்பு அமைப்பு",
        "login.welcome": "வரவேற்பு",
        "login.manage": "கணக்கு மேலாண்மை",
        "login.login_prompt": "உங்கள் கணக்கில் உள்நுழையவும்",
        "login.manage_prompt": "ID, கடவுச்சொல் அல்லது பங்கை மாற்றவும்",
        "login.id": "ID",
        "login.password": "கடவுச்சொல்",
        "login.role": "பங்கு",
        "login.forgot": "கடவுச்சொல்லை மறந்துவிட்டீர்களா",
        "login.submit": "உள்நுழை",
        "login.save": "சேமி",
        "login.role_farmer": "விவசாயி",
        "login.role_analyst": "விவசாய பகுப்பாய்வாளர்",
        "login.role_student": "மாணவர்",
        "login.placeholder_role": "உங்கள் பங்கை தேர்ந்தெடுக்கவும்",
        "farmer.title": "HarvestIQ",
        "farmer.subtitle": "எளிய உள்ளீடுகளை model மதிப்புகளாக மாற்றுகிறது",
        "farmer.submit": "பயிரை கணிக்கவும் (விவசாயி முறை)",
        "analyst.eyebrow": "விவசாய பகுப்பாய்வாளர் வேலைப்பகம்",
        "analyst.title": "வரலாற்று சூழலுடன் துல்லியமான பயிர் கணிப்பு.",
        "analyst.subtitle": "இங்கே நீங்கள் நேரடி அளவுகளை உள்ளிடலாம். இந்த பார்வை prediction, historical summary, feature importance மற்றும் radar comparison ஆகியவற்றைக் காட்டுகிறது.",
        "analyst.submit": "பகுப்பாய்வை தொடங்கு",
        "analyst.inputs": "உள்ளீடுகள்",
        "analyst.alternatives": "மாற்று தேர்வுகள்",
        "analyst.model": "மாதிரி",
        "analyst.result_placeholder": "கணிப்பு செய்த பிறகு summary, importance, radar chart இங்கே தோன்றும்.",
        "analyst.context": "சூழல் எச்சரிக்கைகள்",
        "analyst.summary": "வரலாற்று சுருக்கம்",
        "analyst.reasoning": "மாதிரி ஏன் இந்த பயிரை தேர்ந்தெடுத்தது",
        "analyst.importance": "அம்ச முக்கியத்துவம்",
        "analyst.radar": "ரேடார் ஒப்பீடு",
        "analyst.closest": "அருகிலுள்ள மாற்றுகள்",
        # Farmer form labels
        "farmer.soil_texture": "மண்ணின் அமைப்பு",
        "farmer.soil_texture_sandy": "மணல் உள்ள",
        "farmer.soil_texture_loamy": "மணல் உள்ள களிமண்",
        "farmer.soil_texture_clayey": "களிமண் மாந்தரம்",
        "farmer.soil_texture_silty": "சilt உள்ள",
        "farmer.soil_fertility": "மண்ணின் வளம் பயிற்சி",
        "farmer.soil_fertility_low": "குறைவு",
        "farmer.soil_fertility_medium": "நடுத்தர",
        "farmer.soil_fertility_high": "உயர்",
        "farmer.soil_appearance": "மண்ணின் வெளிப்பாடு",
        "farmer.soil_appearance_normal": "இயல்பான தோற்றத்தை கொண்ட மண்",
        "farmer.soil_appearance_white_crust": "வெள்ளை மேல் பாதுகாப்பு / உப்பு மேற்பரப்பு",
        "farmer.soil_appearance_very_dark": "மிக அடர்ந்த / கரிம தோற்ற மண்",
        "farmer.soil_appearance_sticky_clay": "ஒட்டும் களிமண் / நீரை தக்க வைக்கும் மண்",
        "farmer.soil_appearance_not_sure": "உறுதியாக தெரியவில்லை",
        "farmer.air_humidity": "காற்று ஈரப்பதம் உணர்வு",
        "farmer.humidity_very_dry": "மிக உறைந்த",
        "farmer.humidity_dry": "உறைந்த",
        "farmer.humidity_comfortable": "வசதியான",
        "farmer.humidity_humid": "ஈரமான",
        "farmer.humidity_very_humid": "மிக ஈரமான",
        "farmer.rainfall_pattern": "கடந்த 30 நாட்களில் மழை",
        "farmer.rainfall_very_low": "மிக குறைந்த மழை",
        "farmer.rainfall_light": "இலகு மழை",
        "farmer.rainfall_moderate": "இயல்பான மழை",
        "farmer.rainfall_heavy": "பெரிய மழை",
        "farmer.rainfall_very_heavy": "மிக பெரிய மழை",
        "farmer.temperature_feel": "வெப்ப நிலை உணர்வு",
        "farmer.temperature_cool": "குளிர்ந்த",
        "farmer.temperature_mild": "மிதமான",
        "farmer.temperature_warm": "வெந்நிலைக்கு",
        "farmer.temperature_hot": "மிக சந்தமான",
        # Analyst form labels and hints
        "analyst.nitrogen": "நைட்ரஜன் (N)",
        "analyst.nitrogen_hint": "எதிர்பார்த்த வரம்பு: 10 முதல் 120 kg/ha",
        "analyst.phosphorus": "பாஸ்பரஸ் (P)",
        "analyst.phosphorus_hint": "எதிர்பார்த்த வரம்பு: 10 முதல் 110 kg/ha",
        "analyst.potassium": "பொட்டாசியம் (K)",
        "analyst.potassium_hint": "எதிர்பார்த்த வரம்பு: 10 முதல் 180 kg/ha",
        "analyst.temperature": "வெப்ப நிலை (°C)",
        "analyst.temperature_hint": "எதிர்பார்த்த வரம்பு: 8 முதல் 42 °C",
        "analyst.humidity": "ஈரப்பதம் (%)",
        "analyst.humidity_hint": "எதிர்பார்த்த வரம்பு: 20 முதல் 95%",
        "analyst.ph": "pH நிலை",
        "analyst.ph_hint": "எதிர்பார்த்த வரம்பு: 4.5 முதல் 8.5",
        "analyst.rainfall": "மழை (mm)",
        "analyst.rainfall_hint": "எதிர்பார்த்த வரம்பு: 20 முதல் 300 mm",
        "analyst.run_prediction": "பகுப்பாய்வை தொடங்கவும்",
        "analyst.what_view_title": "இந்த பார்வை பகுப்பாய்வாளருக்கு என்ன தருகிறது",
        "analyst.what_view_text": "மாதிரி வெளிப்பாடு சرафமாত்திரம் பயிர் குறிப்பு அல்ல. இது வரலாற்று பயிர் சுயவிவரம் என்பது உள்ளீட்டால் எவ்வாறு ஒத்திருக்கிறது, கौன உள்ளீடுகள் கணிப்பை தள்ளுங்கள்,இவை அருகிலுள்ள மாற்றுகளுக்கு எவ்வாறு தெரியும் என்பதையும் காட்டுக்கள்.",
        "analyst.badge_prediction": "கணிப்பு + நம்பிக்கை",
        "analyst.badge_summary": "வரலாற்று பயிர் சுள்லசுற்றம்",
        "analyst.badge_importance": "அம்ச முக்கியத்துவம்",
        "analyst.badge_radar": "ரேடார் ஒப்பீடு",
        "analyst.table_feature": "அம்சம்",
        "analyst.table_input": "உள்ளீட்டு",
        "analyst.table_mean": "பயிர் சராசரி",
        "analyst.table_median": "மध्य",
        "analyst.table_range": "வழக்கமான வரம்பு",
        "analyst.table_fit": "பொருத்தம்",
        "analyst.table_placeholder": "ஒரு கணிப்பை செய்தபிறகு வரலாற்று புள்ளிவிபரங்கள் இங்கே தோன்றும்.",
        "analyst.reasoning_placeholder": "விளக்கக் குறிப்புகள் கணிப்பு இயங்குவதன் பிறகு உருவாக்கப்படுகின்றன.",
        "analyst.radar_description": "ரேடார் விளக்கப்படம் பயனரின் உள்ளீட்டை அனுமानித்த பயிரின் வரலாற்று சுயவிவரத்துடனும் அருகிலுள்ள மாற்று பயிர்களுடனும் ஒப்பிடுகிறது.",
        "analyst.alternatives_placeholder": "மாதிரி ஒரு முடிவை உருவாக்கிய பிறகு மாற்று பயிர்கள் இங்கே பட்டியலிடப்படும்।",
        "student.eyebrow": "மாணவர் பகுப்பாய்வு பார்வை",
        "student.title": "விளக்கத்துடன் பயிர் கணிப்பு",
        "student.subtitle": "ஆனலிஸ்ட் பார்வை போலவே 7 எண்ணியல் மதிப்புகளை உள்ளிடவும்; ஆனால் கணிக்கப்பட்ட பயிர், அடுத்த 2 மாற்றுகள், மற்றும் முக்கிய தாக்கத்தை ஏற்படுத்திய அம்சம் மட்டும் காண்பிக்கப்படும்.",
        "student.submit": "மாணவர் கணிப்பை இயக்கவும்",
        "student.panel_title": "கணிப்பு சுருக்கம்",
        "student.panel_placeholder": "பயிர் வரிசை மற்றும் விளக்கத்தை காண கணிப்பை இயக்கவும்.",
        "student.top_crops": "முதல் 3 பயிர்கள்",
        "student.reasoning_title": "ஏன் இந்த பயிர்கள்",
        "student.strongest_title": "அதிக தாக்கம் கொண்ட புலம்",
        "student.inputs": "உள்ளீடுகள்",
    },
}

MODEL_FILENAME = "crop_model.pkl"
DATASET_FILENAME = "Crop_recommendation.csv"

FEATURE_ORDER = ["N", "P", "K", "temp", "humidity", "ph", "rainfall"]

DATASET_COLUMN_MAP = {
    "N": "N",
    "P": "P",
    "K": "K",
    "temp": "temperature",
    "humidity": "humidity",
    "ph": "ph",
    "rainfall": "rainfall",
}

FEATURE_LABELS = {
    "N": "Nitrogen",
    "P": "Phosphorus",
    "K": "Potassium",
    "temp": "Temperature",
    "humidity": "Humidity",
    "ph": "pH",
    "rainfall": "Rainfall",
}

ANALYST_INPUT_FIELDS = {
    "Nitrogen": "N",
    "Phosphorus": "P",
    "Potassium": "K",
    "Temperature": "temp",
    "Humidity": "humidity",
    "pH": "ph",
    "Rainfall": "rainfall",
}

ANALYST_VALIDATION_RULES = {
    "N": {"label": "Nitrogen", "hard_min": 0, "hard_max": 300, "soft_min": 10, "soft_max": 120},
    "P": {"label": "Phosphorus", "hard_min": 0, "hard_max": 300, "soft_min": 10, "soft_max": 110},
    "K": {"label": "Potassium", "hard_min": 0, "hard_max": 400, "soft_min": 10, "soft_max": 180},
    "temp": {"label": "Temperature", "hard_min": -10, "hard_max": 60, "soft_min": 8, "soft_max": 42},
    "humidity": {"label": "Humidity", "hard_min": 0, "hard_max": 100, "soft_min": 20, "soft_max": 95},
    "ph": {"label": "pH", "hard_min": 0, "hard_max": 14, "soft_min": 4.5, "soft_max": 8.5},
    "rainfall": {"label": "Rainfall", "hard_min": 0, "hard_max": 1000, "soft_min": 20, "soft_max": 300},
}

ANALYST_RADAR_COLORS = [
    {"border": "rgba(31, 122, 74, 0.95)", "fill": "rgba(31, 122, 74, 0.16)"},
    {"border": "rgba(28, 116, 199, 0.95)", "fill": "rgba(28, 116, 199, 0.14)"},
    {"border": "rgba(231, 120, 39, 0.95)", "fill": "rgba(231, 120, 39, 0.14)"},
    {"border": "rgba(120, 72, 198, 0.95)", "fill": "rgba(120, 72, 198, 0.14)"},
]

ALLOWED_ROLES = {"Farmer", "Agricultural Analyst", "Student"}
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "agriflask")
MYSQL_USERS_TABLE = os.getenv("MYSQL_USERS_TABLE", "users")

DEFAULT_LANGUAGE = "en"

try:
    with open(MODEL_FILENAME, "rb") as file:
        model = pickle.load(file)
    print(f"Model '{MODEL_FILENAME}' loaded successfully for Farmer pilot.")
except FileNotFoundError:
    model = None
    print(f"WARNING: Model file '{MODEL_FILENAME}' not found. Farmer pilot predictions will fail.")

CROP_DATASET_STATS = {}
GLOBAL_FEATURE_RANGES = {}
ANALYST_FEATURE_IMPORTANCE = []


def _mysql_connect(database: str | None = None):
    connection_config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "autocommit": True,
    }
    if database:
        connection_config["database"] = database
    return mysql.connector.connect(**connection_config)


def initialize_mysql_store() -> bool:
    try:
        connection = _mysql_connect()
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        connection.close()

        connection = _mysql_connect(MYSQL_DATABASE)
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{MYSQL_USERS_TABLE}` (
                `user_id` VARCHAR(255) NOT NULL,
                `password_hash` VARCHAR(255) NOT NULL,
                `role` VARCHAR(64) NOT NULL,
                PRIMARY KEY (`user_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.close()
        connection.close()
        print(f"MySQL connected: {MYSQL_DATABASE}.{MYSQL_USERS_TABLE}")
        return True
    except MySQLError as exc:
        print(f"WARNING: MySQL connection failed: {exc}")
        return False


mysql_ready = initialize_mysql_store()

# Confidence interpretation tuned for 22-class prediction.
LOW_CONFIDENCE_THRESHOLD = 0.20
MODERATE_CONFIDENCE_THRESHOLD = 0.35
AMBIGUITY_MARGIN_THRESHOLD = 0.04

# Qualitative-to-numeric mappings for Farmer mode.
SOIL_FERTILITY_BASE = {
    "low": {"N": 35.0, "P": 30.0, "K": 30.0},
    "medium": {"N": 65.0, "P": 55.0, "K": 50.0},
    "high": {"N": 95.0, "P": 75.0, "K": 70.0},
}

SOIL_TEXTURE_ADJUST = {
    "sandy": {"N": -10.0, "P": -5.0, "K": -10.0},
    "loamy": {"N": 0.0, "P": 0.0, "K": 0.0},
    "clayey": {"N": 5.0, "P": 5.0, "K": 10.0},
    "silty": {"N": 3.0, "P": 4.0, "K": 5.0},
}

SOIL_APPEARANCE_TO_PH = {
    "normal": 6.8,
    "white_crust": 8.1,
    "very_dark": 6.3,
    "sticky_clay": 7.4,
    "not_sure": 6.8,
}

AIR_HUMIDITY_TO_VALUE = {
    "very_dry": 30.0,
    "dry": 45.0,
    "comfortable": 60.0,
    "humid": 75.0,
    "very_humid": 90.0,
}

RAINFALL_TO_VALUE = {
    "very_low": 20.0,
    "light": 40.0,
    "moderate": 90.0,
    "heavy": 180.0,
    "very_heavy": 280.0,
}

TEMPERATURE_TO_VALUE = {
    "cool": 18.0,
    "mild": 25.0,
    "warm": 31.0,
    "hot": 38.0,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def get_selected_language() -> str:
    language = session.get("language", DEFAULT_LANGUAGE)
    return language if language in LANGUAGES else DEFAULT_LANGUAGE


def translate(key: str, language: str | None = None) -> str:
    active_language = language or get_selected_language()
    return TRANSLATIONS.get(active_language, TRANSLATIONS[DEFAULT_LANGUAGE]).get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))


@app.context_processor
def inject_ui_helpers():
    return {
        "current_user": get_current_user(),
        "selected_language": get_selected_language(),
        "languages": LANGUAGES,
        "t": translate,
    }


def load_dataset_statistics(dataset_filename: str) -> tuple[dict, dict]:
    crop_rows = defaultdict(list)

    with open(dataset_filename, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            label = row["label"].strip()
            numeric_row = {feature: float(row[DATASET_COLUMN_MAP[feature]]) for feature in FEATURE_ORDER}
            crop_rows[label].append(numeric_row)

    global_ranges = {}
    for feature in FEATURE_ORDER:
        feature_values = [row[feature] for rows in crop_rows.values() for row in rows]
        global_ranges[feature] = {
            "min": min(feature_values),
            "max": max(feature_values),
        }

    crop_stats = {}
    for crop_name, rows in crop_rows.items():
        crop_stats[crop_name] = {
            "count": len(rows),
            "mean": {feature: mean([row[feature] for row in rows]) for feature in FEATURE_ORDER},
            "median": {feature: median([row[feature] for row in rows]) for feature in FEATURE_ORDER},
            "min": {feature: min(row[feature] for row in rows) for feature in FEATURE_ORDER},
            "max": {feature: max(row[feature] for row in rows) for feature in FEATURE_ORDER},
        }

    return crop_stats, global_ranges


def build_model_feature_importance(active_model) -> list[dict]:
    if active_model is None:
        return []

    raw_scores = getattr(active_model, "feature_importances_", None)
    if raw_scores is None:
        raw_scores = [1.0 / len(FEATURE_ORDER)] * len(FEATURE_ORDER)

    total = float(sum(raw_scores)) or 1.0
    rows = []
    for feature, raw_score in zip(FEATURE_ORDER, raw_scores):
        normalized = float(raw_score) / total
        rows.append({
            "feature": feature,
            "label": FEATURE_LABELS[feature],
            "score": normalized,
            "pct": normalized * 100.0,
        })

    return sorted(rows, key=lambda item: item["score"], reverse=True)


def normalize_value(value: float, feature: str) -> float:
    feature_range = GLOBAL_FEATURE_RANGES.get(feature)
    if not feature_range:
        return 50.0

    low = feature_range["min"]
    high = feature_range["max"]
    if high <= low:
        return 50.0

    return clamp(((value - low) / (high - low)) * 100.0, 0.0, 100.0)


def build_profile_vector(values: dict) -> list[float]:
    return [normalize_value(values[feature], feature) for feature in FEATURE_ORDER]


def get_crop_profile_vector(crop_name: str) -> list[float]:
    crop_stats = CROP_DATASET_STATS.get(crop_name)
    if not crop_stats:
        return [50.0] * len(FEATURE_ORDER)

    return [normalize_value(crop_stats["mean"][feature], feature) for feature in FEATURE_ORDER]


def build_statistical_rows(input_values: dict, predicted_crop: str) -> list[dict]:
    crop_stats = CROP_DATASET_STATS.get(predicted_crop)
    if not crop_stats:
        return []

    rows = []
    for feature in FEATURE_ORDER:
        input_value = float(input_values[feature])
        crop_mean = float(crop_stats["mean"][feature])
        crop_median = float(crop_stats["median"][feature])
        crop_min = float(crop_stats["min"][feature])
        crop_max = float(crop_stats["max"][feature])
        global_range = GLOBAL_FEATURE_RANGES.get(feature, {"min": crop_min, "max": crop_max})
        span = max(global_range["max"] - global_range["min"], 1e-9)
        fit_pct = max(0.0, 100.0 - (abs(input_value - crop_mean) / span) * 100.0)

        rows.append({
            "feature": feature,
            "label": FEATURE_LABELS[feature],
            "input_value": round(input_value, 2),
            "crop_mean": round(crop_mean, 2),
            "crop_median": round(crop_median, 2),
            "crop_min": round(crop_min, 2),
            "crop_max": round(crop_max, 2),
            "difference": round(input_value - crop_mean, 2),
            "within_range": crop_min <= input_value <= crop_max,
            "fit_pct": round(fit_pct, 1),
        })

    return rows


def build_reasoning_points(statistical_rows: list[dict], alternative_crops: list[dict], predicted_crop: str, confidence_pct: float) -> list[str]:
    if not statistical_rows:
        return []

    closest_rows = sorted(statistical_rows, key=lambda row: abs(row["difference"]))[:2]
    strongest_gap = max(statistical_rows, key=lambda row: abs(row["difference"]))

    points = [
        f"{predicted_crop} matches the historical crop profile in {closest_rows[0]['label']} and {closest_rows[1]['label']} more closely than the other inputs.",
        f"{strongest_gap['label']} is the biggest deviation from the crop's average conditions, which helps explain the model confidence of {confidence_pct:.1f}%.",
    ]

    if alternative_crops:
        alt_names = ", ".join(crop["name"] for crop in alternative_crops[:2])
        points.append(f"The nearest alternatives are {alt_names}, so the model is comparing a small cluster of similar crops rather than a single obvious choice.")

    return points


def build_radar_chart_data(input_values: dict, predicted_crop: str, alternative_crops: list[dict]) -> dict:
    datasets = []
    profiles = [
        ("Your input", build_profile_vector(input_values)),
        (f"{predicted_crop} average", get_crop_profile_vector(predicted_crop)),
    ]

    for alt_crop in alternative_crops[:2]:
        profiles.append((f"{alt_crop['name']} average", get_crop_profile_vector(alt_crop["name"])))

    for index, (label, profile) in enumerate(profiles):
        color = ANALYST_RADAR_COLORS[index % len(ANALYST_RADAR_COLORS)]
        datasets.append({
            "label": label,
            "data": [round(point, 2) for point in profile],
            "borderColor": color["border"],
            "backgroundColor": color["fill"],
            "pointBackgroundColor": color["border"],
            "pointBorderColor": color["border"],
            "pointRadius": 3,
            "borderWidth": 2,
            "fill": True,
        })

    return {
        "labels": [FEATURE_LABELS[feature] for feature in FEATURE_ORDER],
        "datasets": datasets,
    }


def build_ranked_crops(probabilities: np.ndarray, predicted_crop: str, limit: int = 3) -> list[dict]:
    sorted_idx = np.argsort(probabilities)[::-1]
    model_classes = getattr(model, "classes_", [])
    ranked_crops = []

    for index in sorted_idx:
        crop_name = model_classes[index] if index < len(model_classes) else predicted_crop
        ranked_crops.append({
            "name": crop_name,
            "probability": round(float(probabilities[index]) * 100.0, 1),
        })
        if len(ranked_crops) == limit:
            break

    return ranked_crops


def build_analyst_output(input_values: dict, predicted_crop: str, probabilities: np.ndarray) -> dict:
    ranked_crops = build_ranked_crops(probabilities, predicted_crop, 4)
    confidence = (ranked_crops[0]["probability"] / 100.0) if ranked_crops else 0.0
    second_best = (ranked_crops[1]["probability"] / 100.0) if len(ranked_crops) > 1 else confidence
    margin = confidence - second_best

    confidence_pct = confidence * 100.0
    if confidence < LOW_CONFIDENCE_THRESHOLD or margin < AMBIGUITY_MARGIN_THRESHOLD:
        result_type = "warning"
        confidence_label = "Low"
    elif confidence < MODERATE_CONFIDENCE_THRESHOLD:
        result_type = "info"
        confidence_label = "Moderate"
    else:
        result_type = "success"
        confidence_label = "High"

    alternative_crops = [crop for crop in ranked_crops if crop["name"] != predicted_crop][:3]

    statistical_rows = build_statistical_rows(input_values, predicted_crop)
    reasoning_points = build_reasoning_points(statistical_rows, alternative_crops, predicted_crop, confidence_pct)
    radar_chart = build_radar_chart_data(input_values, predicted_crop, alternative_crops)

    return {
        "result_type": result_type,
        "confidence_pct": confidence_pct,
        "confidence_label": confidence_label,
        "margin_pct": margin * 100.0,
        "alternative_crops": alternative_crops,
        "statistical_rows": statistical_rows,
        "reasoning_points": reasoning_points,
        "radar_chart": radar_chart,
    }


def build_student_output(input_values: dict, predicted_crop: str, probabilities: np.ndarray) -> dict:
    analysis = build_analyst_output(input_values, predicted_crop, probabilities)
    top_crops = build_ranked_crops(probabilities, predicted_crop, 3)
    strongest_row = None

    if analysis["statistical_rows"]:
        strongest_row = max(analysis["statistical_rows"], key=lambda row: abs(row["difference"]))

    reasoning_points = list(analysis["reasoning_points"][:2])
    if strongest_row:
        gap_direction = "above" if strongest_row["difference"] > 0 else "below"
        reasoning_points.insert(
            0,
            (
                f"{strongest_row['label']} differs the most from {predicted_crop}'s profile. "
                f"Your input is {gap_direction} the crop average here, so the model leans on this field heavily."
            ),
        )

    strongest_feature = None
    if strongest_row:
        strongest_feature = {
            "label": strongest_row["label"],
            "input": strongest_row["input_value"],
            "crop_mean": strongest_row["crop_mean"],
            "difference": strongest_row["difference"],
            "fit": strongest_row["fit_pct"],
        }

    return {
        "result_type": analysis["result_type"],
        "confidence_pct": analysis["confidence_pct"],
        "confidence_label": analysis["confidence_label"],
        "top_crops": top_crops,
        "reasoning_points": reasoning_points,
        "strongest_feature": strongest_feature,
    }


def validate_analyst_values(values: dict) -> str | None:
    out_of_range = []
    for key, val in values.items():
        rule = ANALYST_VALIDATION_RULES[key]
        if val < rule["hard_min"] or val > rule["hard_max"]:
            return (
                f"{rule['label']} must be between {rule['hard_min']} and {rule['hard_max']}. "
                "Please enter a correct value."
            )
        if val < rule["soft_min"] or val > rule["soft_max"]:
            out_of_range.append(f"{rule['label']} ({val})")

    if out_of_range:
        fields = ", ".join(out_of_range)
        return (
            f"The following values are outside the realistic agricultural range: {fields}. "
            "No reliable crop recommendation should be given for these extreme conditions. Please revise the inputs."
        )

    return None


def build_analyst_warnings(values: dict) -> list[str]:
    warnings = []

    temp = values["temp"]
    humidity = values["humidity"]
    ph = values["ph"]
    rainfall = values["rainfall"]
    nitrogen = values["N"]

    if temp > 35 and humidity > 90:
        warnings.append("Extreme heat + very high humidity: fungal diseases are likely.")

    if temp < 10 and rainfall > 250:
        warnings.append("Cold + very high rainfall: flooding or waterlogging risk.")

    if ph < 4.5 and nitrogen > 100:
        warnings.append("Very acidic soil + high nitrogen: nutrient leaching risk.")

    if ph > 8 and rainfall > 250:
        warnings.append("Alkaline soil + excessive rainfall: crusting and nutrient stress may occur.")

    return warnings


try:
    CROP_DATASET_STATS, GLOBAL_FEATURE_RANGES = load_dataset_statistics(DATASET_FILENAME)
    print(f"Dataset '{DATASET_FILENAME}' loaded successfully for analyst summaries.")
except FileNotFoundError:
    CROP_DATASET_STATS = {}
    GLOBAL_FEATURE_RANGES = {}
    print(f"WARNING: Dataset file '{DATASET_FILENAME}' not found. Analyst summaries will be limited.")

ANALYST_FEATURE_IMPORTANCE = build_model_feature_importance(model)


def validate_farmer_inputs(form_data: dict) -> str | None:
    soil_texture = form_data["soil_texture"]
    soil_fertility = form_data["soil_fertility"]
    soil_appearance = form_data["soil_appearance"]
    air_humidity = form_data["air_humidity"]
    rainfall_pattern = form_data["rainfall_pattern"]
    temperature_feel = form_data["temperature_feel"]

    if rainfall_pattern == "very_low" and temperature_feel == "hot":
        return "The combination of very low rainfall and hot temperature is too harsh for a reliable crop recommendation. Please revise the inputs."

    if rainfall_pattern == "very_heavy" and air_humidity in {"dry", "very_dry"}:
        return "Very heavy rainfall with dry air is inconsistent for a real field condition. Please check the rainfall and humidity selections."

    if rainfall_pattern in {"heavy", "very_heavy"} and soil_texture == "sandy" and temperature_feel == "hot":
        return "Hot weather, sandy soil, and heavy rainfall together make the input set unstable for a reliable crop prediction. Please revise the inputs."

    if soil_appearance == "white_crust" and soil_fertility == "high":
        return "White crust on the soil usually suggests salt stress, which conflicts with a high-fertility reading. Please check the soil inputs again."

    if soil_appearance == "not_sure" and rainfall_pattern == "very_low" and temperature_feel == "hot":
        return "The chosen observations suggest a stressed field, so the model cannot make a dependable crop recommendation. Please refine the inputs."

    return None


def map_farmer_inputs_to_features(form_data: dict) -> dict:
    fertility = form_data["soil_fertility"]
    texture = form_data["soil_texture"]
    appearance = form_data["soil_appearance"]
    humidity_level = form_data["air_humidity"]
    rainfall_level = form_data["rainfall_pattern"]
    temp_level = form_data["temperature_feel"]

    base = SOIL_FERTILITY_BASE[fertility]
    adjust = SOIL_TEXTURE_ADJUST[texture]

    n_value = clamp(base["N"] + adjust["N"], 10.0, 120.0)
    p_value = clamp(base["P"] + adjust["P"], 10.0, 110.0)
    k_value = clamp(base["K"] + adjust["K"], 10.0, 180.0)

    return {
        "N": n_value,
        "P": p_value,
        "K": k_value,
        "temp": TEMPERATURE_TO_VALUE[temp_level],
        "humidity": AIR_HUMIDITY_TO_VALUE[humidity_level],
        "ph": SOIL_APPEARANCE_TO_PH[appearance],
        "rainfall": RAINFALL_TO_VALUE[rainfall_level],
    }


def get_user_record(user_id: str) -> dict[str, str] | None:
    try:
        connection = _mysql_connect(MYSQL_DATABASE)
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT user_id, password_hash, role FROM `{MYSQL_USERS_TABLE}` WHERE user_id = %s LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        if isinstance(row, dict):
            return {
                "user_id": str(row.get("user_id", "")),
                "password_hash": str(row.get("password_hash", "")),
                "role": str(row.get("role", "")),
            }
        return None
    except MySQLError:
        return None


def save_user_record(user_id: str, password: str, role: str) -> None:
    try:
        connection = _mysql_connect(MYSQL_DATABASE)
        cursor = connection.cursor()
        cursor.execute(
            f"""
            INSERT INTO `{MYSQL_USERS_TABLE}` (user_id, password_hash, role)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                password_hash = VALUES(password_hash),
                role = VALUES(role)
            """,
            (user_id, generate_password_hash(password), role),
        )
        connection.commit()
        cursor.close()
        connection.close()
    except MySQLError as exc:
        raise RuntimeError(f"MySQL users table is not available: {exc}") from exc


def render_login_page(
    *,
    auth_mode: str = "select",
    status_message: str = "",
    form_user_id: str = "",
    form_role: str = "",
    edit_mode: bool = False,
) -> str:
    return render_template(
        "login.html",
        auth_mode=auth_mode,
        status_message=status_message,
        form_user_id=form_user_id,
        form_role=form_role,
        edit_mode=edit_mode,
    )


def get_current_user() -> dict:
    user_id = session.get("user_id")
    role = session.get("role")

    if not user_id or not role:
        return {"is_authenticated": False, "user_id": "", "role": ""}

    return {
        "is_authenticated": True,
        "user_id": user_id,
        "role": role,
    }


@app.route("/")
def home():
    current_user = get_current_user()
    status_message = request.args.get("status", "")
    return render_template(
        "home.html",
        current_user=current_user,
        status_message=status_message,
    )


@app.route("/set-language", methods=["POST"])
def set_language():
    language = request.form.get("language", DEFAULT_LANGUAGE)
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE

    session["language"] = language
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        user_id = (request.form.get("user_id") or "").strip()
        password = request.form.get("password") or ""
        if not mysql_ready:
            return render_login_page(
                auth_mode="login",
                status_message="MySQL is not available. Set MYSQL_HOST, MYSQL_USER, and MYSQL_PASSWORD, then make sure MySQL is running.",
                form_user_id=user_id,
            )

        if not user_id or not password:
            return render_login_page(
                auth_mode="login",
                status_message="Please fill in both user ID and password.",
                form_user_id=user_id,
            )

        existing_user = get_user_record(user_id)

        if not existing_user:
            return render_login_page(
                auth_mode="login",
                status_message="Invalid credentials.",
                form_user_id=user_id,
            )

        if not check_password_hash(existing_user.get("password_hash", ""), password):
            return render_login_page(
                auth_mode="login",
                status_message="Invalid credentials.",
                form_user_id=user_id,
            )

        session["user_id"] = existing_user["user_id"]
        session["role"] = existing_user.get("role", "")
        return redirect(url_for("home", status="Logged in successfully."))

    current_user = get_current_user()
    auth_mode = (request.args.get("mode") or "select").strip().lower()
    edit_mode = request.args.get("edit") == "1" and current_user["is_authenticated"]

    if edit_mode:
        return render_login_page(
            auth_mode="register",
            form_user_id=current_user["user_id"],
            form_role=current_user["role"],
            edit_mode=True,
        )

    if auth_mode not in {"select", "login", "register"}:
        auth_mode = "select"

    return render_login_page(auth_mode=auth_mode)


@app.route("/register", methods=["POST"])
def register_page():
    current_user = get_current_user()
    user_id = (request.form.get("user_id") or "").strip()
    password = request.form.get("password") or ""
    role = (request.form.get("role") or "").strip()
    edit_mode = request.form.get("edit_mode") == "1"

    if not mysql_ready:
        return render_login_page(
            auth_mode="register",
            status_message="MySQL is not available. Set MYSQL_HOST, MYSQL_USER, and MYSQL_PASSWORD, then make sure MySQL is running.",
            form_user_id=user_id,
            form_role=role,
            edit_mode=edit_mode,
        )

    if not user_id or not role or (not edit_mode and not password):
        return render_login_page(
            auth_mode="register",
            status_message="Please fill in user ID, password, and role.",
            form_user_id=user_id,
            form_role=role,
            edit_mode=edit_mode,
        )

    if role not in ALLOWED_ROLES:
        return render_login_page(
            auth_mode="register",
            status_message="Please select a valid role.",
            form_user_id=user_id,
            form_role=role,
            edit_mode=edit_mode,
        )

    existing_user = get_user_record(user_id)

    if edit_mode:
        if not current_user["is_authenticated"]:
            return redirect(url_for("login_page", mode="register"))

        current_user_doc = get_user_record(current_user["user_id"])
        if current_user_doc is None:
            return render_login_page(
                auth_mode="register",
                status_message="Your account could not be found. Please register again.",
                form_user_id=user_id,
                form_role=role,
                edit_mode=True,
            )

        if user_id != current_user["user_id"] and existing_user:
            return render_login_page(
                auth_mode="register",
                status_message="That user ID already exists. Please choose another one.",
                form_user_id=user_id,
                form_role=role,
                edit_mode=True,
            )

        password_hash = current_user_doc.get("password_hash", "")
        if password:
            password_hash = generate_password_hash(password)

        connection = _mysql_connect(MYSQL_DATABASE)
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE `{MYSQL_USERS_TABLE}`
            SET user_id = %s, password_hash = %s, role = %s
            WHERE user_id = %s
            """,
            (user_id, password_hash, role, current_user["user_id"]),
        )
        connection.commit()
        cursor.close()
        connection.close()

        session["user_id"] = user_id
        session["role"] = role
        return redirect(url_for("home", status="Account updated successfully."))

    if existing_user:
        return render_login_page(
            auth_mode="register",
            status_message="That user ID already exists. Please choose another one.",
            form_user_id=user_id,
            form_role=role,
        )

    save_user_record(user_id, password, role)
    session["user_id"] = user_id
    session["role"] = role
    return redirect(url_for("home", status="Account created successfully."))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home", status="You have logged out."))


@app.route("/go-predict")
def go_predict():
    current_user = get_current_user()
    if not current_user["is_authenticated"]:
        return redirect(url_for("login_page"))

    role = current_user["role"]
    if role == "Farmer":
        return redirect(url_for("farmer_predictor_page"))
    if role == "Agricultural Analyst":
        return redirect(url_for("analyst_predictor_page"))
    if role == "Student":
        return redirect(url_for("student_predictor_page"))

    return redirect(url_for("home", status="Please select a valid role from your account settings."))


@app.route("/farmer-predictor")
def farmer_predictor_page():
    return render_template("farmer_index.html")


@app.route("/farmer-predict", methods=["POST"])
def farmer_predict():
    required_fields = [
        "soil_texture",
        "soil_fertility",
        "soil_appearance",
        "air_humidity",
        "rainfall_pattern",
        "temperature_feel",
    ]

    missing = [field for field in required_fields if not request.form.get(field)]
    if missing:
        return render_template(
            "farmer_index.html",
            prediction_text="Error: please select all input options before predicting.",
            result_type="error",
        )

    if model is None:
        return render_template(
            "farmer_index.html",
            prediction_text="Prediction error: model file not loaded.",
            result_type="error",
        )

    form_data = {field: request.form.get(field) for field in required_fields}
    invalid_reason = validate_farmer_inputs(form_data)
    if invalid_reason:
        return render_template(
            "farmer_index.html",
            prediction_text=invalid_reason,
            result_type="error",
            selected=form_data,
        )

    features_map = map_farmer_inputs_to_features(form_data)
    feature_array = pd.DataFrame([
        {
            "N": features_map["N"],
            "P": features_map["P"],
            "K": features_map["K"],
            "temperature": features_map["temp"],
            "humidity": features_map["humidity"],
            "ph": features_map["ph"],
            "rainfall": features_map["rainfall"],
        }
    ])

    predicted_crop = model.predict(feature_array)[0]
    probabilities = model.predict_proba(feature_array)[0]

    sorted_idx = np.argsort(probabilities)[::-1]
    top_idx = sorted_idx[0]
    second_idx = sorted_idx[1] if len(sorted_idx) > 1 else sorted_idx[0]

    confidence = float(probabilities[top_idx])
    second_best = float(probabilities[second_idx])
    margin = confidence - second_best

    confidence_pct = confidence * 100.0

    if confidence < LOW_CONFIDENCE_THRESHOLD or margin < AMBIGUITY_MARGIN_THRESHOLD:
        result_type = "warning"
        confidence_label = "Low"
    elif confidence < MODERATE_CONFIDENCE_THRESHOLD:
        result_type = "info"
        confidence_label = "Moderate"
    else:
        result_type = "success"
        confidence_label = "High"

    prediction_text = (
        f"Predicted crop: {predicted_crop}\n"
        f"Confidence: {confidence_pct:.1f}% ({confidence_label})"
    )

    return render_template(
        "farmer_index.html",
        prediction_text=prediction_text,
        result_type=result_type,
        mapped_features=features_map,
        selected=form_data,
    )


@app.route("/analyst-predictor")
def analyst_predictor_page():
    return render_template(
        "analyst_index.html",
        feature_importance=ANALYST_FEATURE_IMPORTANCE,
        radar_chart={},
        statistical_rows=[],
        reasoning_points=[],
        alternative_crops=[],
        warnings=[],
    )


@app.route("/analyst-predict", methods=["POST"])
def analyst_predict():
    required_fields = list(ANALYST_INPUT_FIELDS.keys())

    missing = [field for field in required_fields if not request.form.get(field)]
    if missing:
        return render_template(
            "analyst_index.html",
            prediction_text="Error: please fill in all numeric input fields before predicting.",
            result_type="error",
            feature_importance=ANALYST_FEATURE_IMPORTANCE,
        )

    if model is None:
        return render_template(
            "analyst_index.html",
            prediction_text="Prediction error: model file not loaded.",
            result_type="error",
            feature_importance=ANALYST_FEATURE_IMPORTANCE,
        )

    raw_form_data = {field: (request.form.get(field) or "").strip() for field in required_fields}

    try:
        numeric_values = {
            ANALYST_INPUT_FIELDS[field]: float(value)
            for field, value in raw_form_data.items()
        }
    except ValueError:
        return render_template(
            "analyst_index.html",
            prediction_text="Error: all inputs must be valid numeric values.",
            result_type="error",
            selected=raw_form_data,
            feature_importance=ANALYST_FEATURE_IMPORTANCE,
        )

    invalid_reason = validate_analyst_values(numeric_values)
    if invalid_reason:
        return render_template(
            "analyst_index.html",
            prediction_text=invalid_reason,
            result_type="error",
            selected=raw_form_data,
            feature_importance=ANALYST_FEATURE_IMPORTANCE,
        )

    values = [numeric_values[feature] for feature in FEATURE_ORDER]
    feature_array = pd.DataFrame([
        {
            "N": numeric_values["N"],
            "P": numeric_values["P"],
            "K": numeric_values["K"],
            "temperature": numeric_values["temp"],
            "humidity": numeric_values["humidity"],
            "ph": numeric_values["ph"],
            "rainfall": numeric_values["rainfall"],
        }
    ])

    predicted_crop = model.predict(feature_array)[0]
    probabilities = model.predict_proba(feature_array)[0]

    analysis = build_analyst_output(numeric_values, predicted_crop, probabilities)
    warnings = build_analyst_warnings(numeric_values)

    prediction_text = (
        f"Predicted crop: {predicted_crop}\n"
        f"Confidence: {analysis['confidence_pct']:.1f}% ({analysis['confidence_label']})\n"
        f"Margin to next best crop: {analysis['margin_pct']:.1f}%"
    )

    return render_template(
        "analyst_index.html",
        prediction_text=prediction_text,
        result_type=analysis["result_type"],
        selected=raw_form_data,
        feature_importance=ANALYST_FEATURE_IMPORTANCE,
        statistical_rows=analysis["statistical_rows"],
        reasoning_points=analysis["reasoning_points"],
        radar_chart=analysis["radar_chart"],
        alternative_crops=analysis["alternative_crops"],
        warnings=warnings,
    )


@app.route("/student-predictor")
def student_predictor_page():
    return render_template("student_index.html")


@app.route("/student-predict", methods=["POST"])
def student_predict():
    required_fields = list(ANALYST_INPUT_FIELDS.keys())

    missing = [field for field in required_fields if not request.form.get(field)]
    if missing:
        return render_template(
            "student_index.html",
            prediction_text="Error: please fill in all numeric input fields before predicting.",
            result_type="error",
        )

    if model is None:
        return render_template(
            "student_index.html",
            prediction_text="Prediction error: model file not loaded.",
            result_type="error",
        )

    raw_form_data = {field: (request.form.get(field) or "").strip() for field in required_fields}

    try:
        numeric_values = {
            ANALYST_INPUT_FIELDS[field]: float(value)
            for field, value in raw_form_data.items()
        }
    except ValueError:
        return render_template(
            "student_index.html",
            prediction_text="Error: all inputs must be valid numeric values.",
            result_type="error",
            selected=raw_form_data,
        )

    invalid_reason = validate_analyst_values(numeric_values)
    if invalid_reason:
        return render_template(
            "student_index.html",
            prediction_text=invalid_reason,
            result_type="error",
            selected=raw_form_data,
        )

    feature_array = pd.DataFrame([
        {
            "N": numeric_values["N"],
            "P": numeric_values["P"],
            "K": numeric_values["K"],
            "temperature": numeric_values["temp"],
            "humidity": numeric_values["humidity"],
            "ph": numeric_values["ph"],
            "rainfall": numeric_values["rainfall"],
        }
    ])

    predicted_crop = model.predict(feature_array)[0]
    probabilities = model.predict_proba(feature_array)[0]
    analysis = build_student_output(numeric_values, predicted_crop, probabilities)

    prediction_text = (
        f"Predicted crop: {predicted_crop}\n"
        f"Confidence: {analysis['confidence_pct']:.1f}% ({analysis['confidence_label']})"
    )

    return render_template(
        "student_index.html",
        prediction_text=prediction_text,
        result_type=analysis["result_type"],
        selected=raw_form_data,
        top_crops=analysis["top_crops"],
        reasoning_points=analysis["reasoning_points"],
        strongest_feature=analysis["strongest_feature"],
    )


if __name__ == "__main__":
    app.run(debug=True)
