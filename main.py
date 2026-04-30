from flask import Flask, render_template, request, redirect, url_for
import numpy as np
import pickle

# 1. Initialize Flask App
app = Flask(__name__)

# --- Load the Trained Model Globally ---
MODEL_FILENAME = 'crop_model.pkl'

try:
    with open(MODEL_FILENAME, 'rb') as file:
        model = pickle.load(file)
    print(f"✅ Model '{MODEL_FILENAME}' loaded successfully.")
except FileNotFoundError:
    model = None
    print(f"❌ WARNING: Model file '{MODEL_FILENAME}' not found. Prediction will fail.")


# --- Validation Rules ---
# Hard limits: physically impossible values (invalid input error)
# Soft limits: based on realistic agricultural conditions from the dataset
VALIDATION_RULES = {
    'N':        {'label': 'Nitrogen',    'hard_min': 0,   'hard_max': 300,  'soft_min': 10,   'soft_max': 120},
    'P':        {'label': 'Phosphorus',  'hard_min': 0,   'hard_max': 300,  'soft_min': 10,   'soft_max': 110},
    'K':        {'label': 'Potassium',   'hard_min': 0,   'hard_max': 400,  'soft_min': 10,   'soft_max': 180},
    'temp':     {'label': 'Temperature', 'hard_min': -10, 'hard_max': 60,   'soft_min': 8,    'soft_max': 42},
    'humidity': {'label': 'Humidity',    'hard_min': 0,   'hard_max': 100,  'soft_min': 20,   'soft_max': 95},
    'ph':       {'label': 'pH',          'hard_min': 0,   'hard_max': 14,   'soft_min': 4.5,  'soft_max': 8.5},
    'rainfall': {'label': 'Rainfall',    'hard_min': 0,   'hard_max': 1000, 'soft_min': 20,   'soft_max': 300},
}

# --- Domain-Aware Crop Suitability Rules ---
# Temperature preferences by crop category (in °C)
CROP_TEMPERATURE_RANGES = {
    'temperate': (8, 25),      # apple, grapes, orange, coffee
    'subtropical': (15, 28),   # banana, mango, papaya, coconut
    'tropical': (20, 35),      # rice, cotton, jute
    'cool_season': (10, 25),   # maize, chickpea, kidneybeans, lentil, pigeonpeas, mothbeans, mungbean, blackgram
    'warm': (18, 32),          # watermelon, muskmelon, pomegranate
}

# pH preferences by crop
CROP_PH_RANGES = {
    'rice': (5.5, 7.5), 'maize': (6.0, 8.0), 'chickpea': (6.5, 8.0),
    'kidneybeans': (5.5, 7.0), 'pigeonpeas': (5.5, 8.0), 'mothbeans': (6.0, 8.0),
    'mungbean': (5.5, 7.0), 'blackgram': (5.5, 7.5), 'lentil': (6.0, 8.0),
    'pomegranate': (6.0, 8.5), 'banana': (5.5, 7.5), 'mango': (5.5, 7.5),
    'grapes': (5.5, 8.0), 'watermelon': (6.0, 8.0), 'muskmelon': (6.0, 8.0),
    'apple': (5.5, 7.0), 'orange': (5.5, 7.5), 'papaya': (5.5, 8.0),
    'coconut': (5.5, 8.5), 'cotton': (6.0, 8.5), 'jute': (5.5, 8.0), 'coffee': (5.5, 6.5),
}

# Confidence interpretation for 22-class model
LOW_CONFIDENCE_THRESHOLD = 0.25
MODERATE_CONFIDENCE_THRESHOLD = 0.40
AMBIGUITY_MARGIN_THRESHOLD = 0.08


# ---------------------------------------------

# 2. Home Route: Serves the landing page
@app.route('/')
def home():
    return render_template('home.html')


# 3. Predictor Page Route: Serves the existing prediction form
@app.route('/predictor')
def predictor_page():
    return render_template('index.html')


# 4. Login Route: Serves role-based login UI
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        # Temporary flow: accept any login values and continue to predictor UI.
        return redirect(url_for('predictor_page'))

    return render_template('login.html')


# 5. Prediction Route: The connection point
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    """Receives form data, validates it with domain rules, and returns crop prediction with confidence."""

    if request.method == 'GET':
        return render_template('index.html')

    try:
        # 3.1. Extract the 7 input features from the form
        raw_form_data = {
            'N': request.form.get('Nitrogen'),
            'P': request.form.get('Phosphorus'),
            'K': request.form.get('Potassium'),
            'temp': request.form.get('Temperature'),
            'humidity': request.form.get('Humidity'),
            'ph': request.form.get('pH'),
            'rainfall': request.form.get('Rainfall')
        }

        # --- Input Validation ---

        # 3.2. Check for missing or empty values
        for key, value in raw_form_data.items():
            if value is None or not value.strip():
                label = VALIDATION_RULES[key]['label']
                return render_template('index.html',
                    prediction_text=f"❌ Error: The '{label}' field is required. Please fill in all inputs.")

        # Values are guaranteed to be non-empty strings after validation.
        form_data = {}
        for key, value in raw_form_data.items():
            if value is not None:
                form_data[key] = value.strip()

        # 3.3. Convert to floats
        N = float(form_data['N'])
        P = float(form_data['P'])
        K = float(form_data['K'])
        temp = float(form_data['temp'])
        humidity = float(form_data['humidity'])
        ph = float(form_data['ph'])
        rainfall = float(form_data['rainfall'])

        values = {'N': N, 'P': P, 'K': K, 'temp': temp, 'humidity': humidity, 'ph': ph, 'rainfall': rainfall}

        # 3.4. HARD LIMIT CHECK — physically impossible values
        for key, val in values.items():
            rule = VALIDATION_RULES[key]
            if val < rule['hard_min'] or val > rule['hard_max']:
                return render_template('index.html',
                    prediction_text=f"❌ Invalid Input: {rule['label']} must be between {rule['hard_min']} and {rule['hard_max']}. Please enter a correct value.")

        # 3.5. SOFT LIMIT CHECK — absurd values outside realistic agricultural range
        out_of_range = []
        for key, val in values.items():
            rule = VALIDATION_RULES[key]
            if val < rule['soft_min'] or val > rule['soft_max']:
                out_of_range.append(f"{rule['label']} ({val})")

        if out_of_range:
            fields = ', '.join(out_of_range)
            return render_template('index.html',
                prediction_text=f"⚠️ Warning: The following values are outside realistic agricultural range: {fields}. No realistic crop exists for these extreme conditions. Please revise your inputs.")

        # 3.6. DOMAIN AWARENESS CHECK — combine temp + humidity + pH for logical consistency
        warnings = []
        
        # Check if temperature + humidity + rainfall combination is physically plausible for agriculture
        if temp > 35 and humidity > 90:
            warnings.append("Extreme heat + very high humidity: fungal diseases likely.")
        
        if temp < 10 and rainfall > 250:
            warnings.append("Cold + very high rainfall: flooding/waterlogging risk.")
        
        if ph < 4.5 and N > 100:
            warnings.append("Very acidic soil + high nitrogen: nutrient leaching risk.")
        
        if ph > 8 and rainfall > 250:
            warnings.append("Alkaline soil + excessive rainfall: alkaline crust formation.")

        # 3.7. Prepare the data for the model (must be a 2D array)
        features = np.array([[N, P, K, temp, humidity, ph, rainfall]])

        prediction_result = "❌ Prediction Error: Model not loaded."
        confidence_message = ""

        if model:
            # 3.8. Get prediction and confidence probabilities
            predicted_crop = model.predict(features)[0]
            
            # Get probability for all classes
            try:
                probabilities = model.predict_proba(features)[0]
                sorted_probabilities = np.sort(probabilities)[::-1]
                confidence = float(sorted_probabilities[0])
                second_best = float(sorted_probabilities[1]) if len(sorted_probabilities) > 1 else 0.0
                margin = confidence - second_best

                confidence_pct = confidence * 100
                if confidence < LOW_CONFIDENCE_THRESHOLD or margin < AMBIGUITY_MARGIN_THRESHOLD:
                    confidence_message = (
                        f"⚠️ <strong>Low Confidence:</strong> Top prediction is close to another crop "
                        f"(confidence: {confidence_pct:.1f}%, margin: {margin*100:.1f}%)."
                    )
                    prediction_result = (
                        f"🤔 <strong>Predicted: {predicted_crop}</strong><br/>"
                        f"Confidence: {confidence_pct:.1f}%<br/>{confidence_message}"
                    )
                elif confidence < MODERATE_CONFIDENCE_THRESHOLD:
                    prediction_result = (
                        f"✅ <strong>Predicted crop: {predicted_crop}</strong><br/>"
                        f"Confidence: {confidence_pct:.1f}% (Moderate confidence)"
                    )
                else:
                    prediction_result = (
                        f"✅ <strong>The optimal crop is: {predicted_crop}</strong><br/>"
                        f"Confidence: {confidence_pct:.1f}%"
                    )
            except Exception:
                # If probability prediction fails, just show the prediction
                prediction_result = f'✅ The optimal crop is: {predicted_crop}'
        
        # Add domain warnings if any
        if warnings:
            warning_text = '<br/>'.join([f'⚠️ {w}' for w in warnings])
            prediction_result += f'<br/><br/>Domain Warnings:<br/>{warning_text}'

        # 3.9. Return the result
        return render_template('index.html', prediction_text=prediction_result)

    except ValueError:
        return render_template('index.html',
            prediction_text="❌ Error: All inputs must be valid numeric values.")

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        return render_template('index.html', prediction_text=f"❌ {error_message}")


if __name__ == '__main__':
    app.run(debug=True)