from flask import Flask, render_template, request, redirect, url_for, session
import pyrebase
import re
import requests
import urllib.parse
import firebase_admin
from datetime import datetime, timedelta
from firebase_admin import credentials, db
from functools import wraps

app = Flask(__name__)
app.secret_key = "YourSecretKey"

# Initialize Firebase
firebaseConfig = {
    'apiKey': "YOUR API KEY",
    'authDomain': "YOUR AUTH DOMAIN",
    'projectId': "YOUR PROJECT ID ",
    'storageBucket': "YOUR STORAGE BUCKET",
    'messagingSenderId': "YOUR MESSAGING SENDER ID",
    'appId': "YOUR APP ID",
    'measurementId': "YOUR MEASUREMENT ID",
    'databaseURL': "YOUR DATABASE URL"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
database = firebase.database()

cred = credentials.Certificate(
   "<PATH TO serviceAccountKey.json>"
)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'YOUR DATABASE URL'
})

# Email validation function
def is_valid_email(email):
    # Use regular expression to validate email format
    return re.match(r"[^@]+@srmist\.edu\.in", email)

# Admin check decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        user = session['user']
        email = user['email']
        admins = ['bs1329@srmist.edu.in']  # List of admin emails
        if email not in admins:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    user_data = get_users_data()
    return render_template('users.html', users=user_data)

def get_users_data():
    ref = db.reference('users')
    users_snapshot = ref.get()
    users = []
    for key, value in users_snapshot.items():
        user = value
        user['id'] = key
        github_username = user.get('git_link', '').split('/')[-1]
        timestamp = get_last_commit(github_username)
        utc_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        ist_difference = timedelta(hours=5, minutes=30)
        ist_time = utc_time + ist_difference
        final_time = ist_time.strftime("%d-%m-%Y , %I:%M %p")
        user['last_commit'] = final_time
        users.append(user)
    return users

def get_last_commit(github_username):
    url = f"https://api.github.com/users/{github_username}/events/public"
    response = requests.get(url)
    if response.status_code == 200:
        events = response.json()
        for event in events:
            if event['type'] == 'PushEvent':
                last_commit = event['created_at']
                return last_commit
    return None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        register_number = request.form['register_number']
        phone_number = request.form['phone_number']
        github_link = request.form['git_link']
        
        if not is_valid_email(email):
            return "Please use your SRMIST email for sign Up"
        
        try:
            encoded = urllib.parse.quote(email, safe="")
            
            users = database.child('users').get()
            if users.each():
                for user in users.each():
                    user_data = user.val()
                    if user_data.get('email') == email:
                        return "This email is already signed up. Please go back to the login page."
            
        except Exception as e:
            return str(e)      
        
        try:
            user = auth.create_user_with_email_and_password(email, password)
            uid = user['localId']

            user_data = {
                'name': name,
                'register_number': register_number,
                'phone_number': phone_number,
                'email': email,
                'git_link': github_link,
                'role': 'Member'
            }
            database.child('users').child(uid).set(user_data)

            return redirect(url_for('login'))
        except Exception as e:
            return render_template('signup.html', error=str(e))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = {
                'idToken': user['idToken'],
                'email': email
            }
            admins = ['bs1329@srmist.edu.in']
            if email in admins:
                return render_template('admin.html')
            else:
                return redirect(url_for('dashboard'))
        except Exception as e:
            return render_template('login.html', error=str(e))

    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        try:
            auth.send_password_reset_email(email)
            return "Password reset email sent. Please check your email."
        except Exception as e:
            return "An error occurred: " + str(e)
    return render_template('forget.html')

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        user = session['user']
        return render_template('dashboard.html', user=user)
    else:
        return redirect(url_for('login'))

@app.route('/logout', methods=["POST", "GET"])
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
