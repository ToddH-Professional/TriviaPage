from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from google.cloud import secretmanager
from google.auth import credentials
from google_auth_oauthlib.flow import Flow
from database import db, User
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate

import requests
import random
import time
import logging
import json
import os
import re

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Set up Flask-Login and Flask-Bcrypt
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

# Load user from the db
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Get the user by ID from the database

# Set up logging
logger = logging.getLogger(__name__)

class MaskSensitiveData(logging.Filter):
    def filter(self, record):
        record.msg = self.mask_tokens(str(record.msg))
        return True

    def mask_tokens(self, log_message):
        # Define multiple regex patterns for different sensitive fields
        patterns = [
            (r'(access_token=)[^\s]+', r'\1****'),  # Mask access tokens
            (r'(id_token=)[^\s]+', r'\1****'),      # Mask ID tokens
            (r'(refresh_token=)[^\s]+', r'\1****'), # Mask refresh tokens
            (r'(Authorization: Bearer )\S+', r'\1****'), # Mask Authorization headers
            (r'(client_secret=)[^\s]+', r'\1****'), # Mask OAuth client secrets
            (r'(code=)[^\s]+', r'\1****'),         # Mask auth codes from OAuth
        ]

        # Apply each pattern to mask sensitive data
        for pattern, replacement in patterns:
            log_message = re.sub(pattern, replacement, log_message, flags=re.IGNORECASE)

        return log_message

# Apply the filter to your logger
logger.setLevel(logging.DEBUG)  # Keep debug mode on
mask_filter = MaskSensitiveData()

# Apply filter to all handlers
for handler in logger.handlers:
    handler.addFilter(mask_filter)

# If no handlers exist, create one
if not logger.hasHandlers():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.addFilter(mask_filter)
    logger.addHandler(console_handler)

    
# Initialize the players' score
player_score = {}

# The index page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html') # Render the index page if it's a GET request

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

#------ SELF REGISTRATION ------ #
   
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
        
        # Ensure the password field is not empty
        if not password:
            flash('Password is required', 'danger')
            return redirect(url_for('register'))
        
        # Create new user and add to DB
        new_user = User(username=username, email=email, score=0)
        new_user.set_password(password)  # Hash using bcrypt

        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
    
        # Find user in the database
        user = User.query.filter_by(username=username).first()

        if user:
            if user.password:  # Check if a password exists (i.e., non-Google user)
                if user and bcrypt.check_password_hash(user.password_hash, password):
                    # If the user is found and the password matches, log the user in
                    login_user(user)  # This stores user.id in the session, not the username
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('index'))                
            else:
                    flash('Invalid password', 'danger')
                    return redirect(url_for('login'))
        else:
            flash('This account uses Google Login. Please sign in with Google.', 'warning')
            return redirect(url_for('login'))
    flash('User not found', 'danger')
    return redirect(url_for('index'))

#------ End of SELF REGISTRATION ------ #

#------ GOOGLE LOGIN ------#

# Determine the redirect URI based on environment
if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
    redirect_uri = 'https://' + os.getenv('RAILWAY_PUBLIC_DOMAIN') + '/callback'
else:
    # Default for local development
    redirect_uri = 'https://8c86-68-97-137-104.ngrok-free.app/callback'

# Determine which credentials file to use
if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    # Get the credentials directly from the environment variable
    google_credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    # Setup Google Secret Manager client
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(google_credentials_json)
    )
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
  
    # Define your project ID and secret name
    #client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    

    # Build the secret name path
    name = f"projects/364391087897/secrets/triviapage-oauth-secret/versions/latest"

    # Access the secret
    response = client.access_secret_version(request={"name": name})
    client_secret_json = response.payload.data.decode("UTF-8")

    # Write to a temp file (OAuth requires a file, not a string)
    client_secret_file = "/tmp/client_secret.json"
    with open(client_secret_file, "w") as f:
        f.write(client_secret_json)
        
else:
    # Local development
    client_secret_file = os.getenv('GOOGLE_CLIENT_SECRET_PATH', "client_secret.json")

@app.route('/googlelogin')
def googlelogin():  
    # Initialize OAuth2 flow
    flow = Flow.from_client_secrets_file(
        client_secret_file,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=redirect_uri
    )
    # Pass the redirect_uri dynamically when creating the flow, not here
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    # Initialize OAuth2 flow
    flow = Flow.from_client_secrets_file(
        client_secret_file,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=redirect_uri
    )

    auth_response = request.url.replace("http://", "https://")  
    token = flow.fetch_token(authorization_response=auth_response)
    credentials = flow.credentials

    # Use the credentials to get user info
    response = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo', 
        headers={'Authorization': f'Bearer {credentials.token}'}
    ) 

    user_info = response.json()

    # Ensure state matches to prevent CSRF attacks
    if session.get('state') != request.args.get('state'):
        return 'State mismatch error', 400
    
    email = user_info.get('email')
    username = user_info.get('name')  # Or use 'email' as username if you prefer

    # Check if user already exists
    user = User.query.filter_by(email=email).first()

    if not user:
            # Create a new user with a default score
            user = User(username=username, email=email, score=0)
            db.session.add(user)
            db.session.commit()

    # Log the user in
    login_user(user)
    flash('Logged in successfully with Google!', 'success')

    return redirect(url_for('index'))
#------ End of GOOGLE LOGIN ------#

#------ This is the database section -----#

# Load database URL from environment
if os.getenv('DATABASE_URL'):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL')      
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_PUBLIC_URL") 
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)
migrate = Migrate(app, db)

#------ END OF DB FUNCTIONS ------#

# Create a player session
def initialize_player_session(username):
    """Initialize the player session for a single player if it's not already set."""
    if 'username' not in session:
        session['username'] = username  # Store the player's name in the session

    if 'score' not in session:
        session['score'] = 0  # Initialize the player's score if not set


@app.route('/choose_category', methods=['GET', 'POST'])
def choose_category():    
    def generate_categories(*category_tuples):
    # Generate list of dictionaries from tuples.  The name is needed for the API call later
        return [{"name": name, "displayname": display} for name, display in category_tuples]

    categories = generate_categories(
    ("music", "Music"),
    ("sport_and_leisure", "Sport and Leisure"),
    ("film_and_tv", "Film and TV"),
    ("arts_and_literature", "Arts and Literature"),
    ("history", "History"),
    ("society_and_culture", "Society and Culture"),
    ("science", "Science"),
    ("geography", "Geography"),
    ("food_and_drink", "Food and Drink"),
    ("general_knowledge", "General Knowledge")
    )

    # Checks if players exist or not
    username = current_user.username
    if not username:
        return redirect(url_for('index'))

    # Create a player session for names and scores
    initialize_player_session(username)

    if request.method == 'POST':
        # Get selected category ID and difficulty
        chosen_category_id = request.form['category']
        difficulty = request.form['difficulty']

        # Redirect to the ask_question page with the selected category ID and difficulty
        return redirect(url_for('ask_question', category=chosen_category_id, difficulty=difficulty))

    return render_template('choose_category.html', 
                            categories=categories)

@app.route('/ask_question', methods=['GET'])
def ask_question():
    # Checks if players exist or not
    username = current_user.username
    if not username:
        return redirect(url_for('index'))

    # Create a session to hold data between pages
    initialize_player_session(username)

    # Ensure Flask registers session changes
    session.modified = True 

    # Try to get category and difficulty from request args first, fallback to session
    category = request.args.get('category') or session.get('category')
    difficulty = request.args.get('difficulty') or session.get('difficulty')

    if not category or not difficulty:
        logger.error("Category or difficulty is missing! Redirecting to category selection.")
        return redirect(url_for('choose_category'))  # Redirect if missing

    # Saving just about everything to the session.  I'm not sure what all will be used
    session['category'] = category 
    session['difficulty'] = difficulty

    url = f"https://the-trivia-api.com/v2/questions?categories={category}&difficulties={difficulty}&limit=1"  

    # Pulls the question and answers
    try:
        response = requests.get(url)
        # Logging the json output
        logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code} | Response Body: {json.dumps(response.json(), indent=2)}")
        # For timed retries.  When it returns 429 wait 5 seconds which is their rate limit
        if response.status_code == 429:
            time.sleep(5)
            response = requests.get(url)
            # Log the request details for the retry
            logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code}")
        # Here is what happens after success
        if response.status_code == 200:
            logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code}")
            question_data = response.json()[0]
            
            # Answers get saved
            answers = question_data['incorrectAnswers'] + [question_data['correctAnswer']]
            random.shuffle(answers)  # Shuffle so the correct answer isn't always in the same spot 

            #Save the question_data as question.  
            session['question'] = question_data  # Save the question for the next page      
                 
        else:
            logger.error(f"Error fetching question. Status code: {response.status_code}")
            return "Error occurred while fetching the question."    

        return render_template('ask_question.html', 
                           question=question_data['question'], 
                           answers=answers)
    
    except Exception as e:
        logger.error(f"Error fetching question: {str(e)}")
        return f"Error occurred: {str(e)}"
        

@app.route('/answer', methods=['GET', 'POST'])
def answer():
    logger.info(f"Session Data: { session['difficulty'] }")  
    # In case someone goes directly to the page
    if request.method == ['GET'] :
        return redirect(url_for('index'))
    
    # Checks if players exist or not
    username = current_user.username

    if not username:
        return redirect(url_for('index')) 
         
    user = User.query.filter_by(username=username).first() # Fetch the user from the database

    # Save the selected answer into the session    
    selected_answer = request.form.get('answer')

    if not selected_answer:
        logger.error("No answer selected!")
        return redirect(url_for('ask_question'))  # If no answer is selected, redirect back
        
    session['selected_answer'] = selected_answer  # Save the selected answer to session 

    # Get the correct answer from session
    question = session.get('question')
    if not question:
        logger.error("No question found in session!")
        return redirect(url_for('ask_question'))  # Redirect to fetch a new question

    correctAnswer = question.get('correctAnswer')  

    if selected_answer == correctAnswer:
        # Determine points based on difficulty
        if session['difficulty'] == 'easy':
            points = 1
        elif session['difficulty'] == 'medium':
            points = 2
        elif session['difficulty'] == 'hard':
            points = 3
          
        user.score += points  # Add the calculated points
        score = user.score
        session.modified = True  # Ensure session updates are saved 
    else:
        score = user.score

    # Commit the score to the db
    db.session.commit()
    return render_template('answer.html', 
                           selected_answer=selected_answer, 
                           correctAnswer=correctAnswer,
                           score=score)

    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create all tables if they don't exist
    app.run(debug=True)
