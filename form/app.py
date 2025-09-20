from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # for session management

# Hardcoded admin credentials
ADMIN_ID = "admin123"
ADMIN_PW = "pass123"

# Load existing feedback (or create empty)
FEEDBACK_FILE = "feedback_data.json"
try:
    with open(FEEDBACK_FILE, "r") as f:
        feedback_data = json.load(f)
except:
    feedback_data = []

# ------------------- Routes -------------------

@app.route('/')
def index():
    return render_template("index.html")


# User login → just redirect to feedback form
@app.route('/user-login')
def user_login():
    return redirect(url_for('feedback_form'))


# Admin login page
@app.route('/admin-login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_id = request.form.get("admin_id")
        admin_pw = request.form.get("admin_pw")
        if admin_id == ADMIN_ID and admin_pw == ADMIN_PW:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid ID or Password", "danger")
    return render_template("login.html")


# User Feedback form
@app.route('/feedback', methods=["GET", "POST"])
def feedback_form():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        product = request.form.get("product")
        rating = int(request.form.get("rating"))
        feedback_type = request.form.get("type")
        message = request.form.get("message")
        date = datetime.now().strftime("%Y-%m-%d")
        sentiment = get_sentiment(rating)

        new_feedback = {
            "name": name,
            "email": email,
            "product": product,
            "rating": rating,
            "type": feedback_type,
            "message": message,
            "date": date,
            "sentiment": sentiment
        }
        feedback_data.insert(0, new_feedback)
        save_feedback()
        return render_template("feedback.html", thank_you=True)
    return render_template("feedback.html", thank_you=False)


# Dashboard page (admin only)
@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template("dashboard.html", feedback_data=feedback_data)


# Logout admin
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


# ------------------- Helper Functions -------------------

def save_feedback():
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback_data, f, indent=2)


def get_sentiment(rating):
    if rating >= 4:
        return "positive"
    elif rating <= 2:
        return "negative"
    else:
        return "neutral"


# ------------------- Run Server -------------------
if __name__ == "__main__":
    app.run(debug=True)
