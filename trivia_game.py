from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from google.cloud import secretmanager
from google.auth import credentials
from google_auth_oauthlib.flow import Flow
import requests
import random
import time
import logging
import json
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the players' scores and names
players_scores = {}
player_order = []  # To store the order of players
current_player_index = 0

# The index page
@app.route('/', methods=['GET', 'POST'])
def index():
    
    if request.method == 'POST':
        num_players = int(request.form['num_players'])  # Get number of players from the form
        session['num_players'] = num_players  # Store the number of players in the session
        return redirect(url_for('get_names'))  # Redirect to the player names page
    
    return render_template('index.html')  # Render the index page if it's a GET request

# For google oauth
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
    project_id = "triviapage"
    version_id = "latest"
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    # Build the secret name path
    name = f"projects/{project_id}/secrets/{client_secret}/versions/{version_id}"

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

# Initialize OAuth2 flow
flow = Flow.from_client_secrets_file(
    client_secret_file,
    scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_uri=redirect_uri
)

@app.route('/login')
def login():  
    logger.info(f"Redirect URI before flow: {redirect_uri}")    
    # Pass the redirect_uri dynamically when creating the flow, not here
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    logger.info(f"Redirecting to Google authorization URL: {authorization_url}")
    return redirect(authorization_url)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/callback')
def callback():
    auth_response = request.url.replace("http://", "https://")    
    logger.info(f"Auth response URL: {auth_response}")    

    #logger.info(f"Request state: {request.args.get('state')}")
    token = flow.fetch_token(authorization_response=auth_response)
    # Get the user's profile information
    #credentials = flow.credentials
    #logger.info(f"Logged in as: {credentials.id_token.get('email')}")    
    # Ensure state matches to prevent CSRF attacks
    #if session.get('state') != request.args.get('state'):
        #return 'State mismatch error', 400

    return redirect(url_for('index'))

# Get the names of players
@app.route('/get_names', methods=['GET', 'POST'])
def get_names():
    # Get the number of players from the session
    num_players = session.get('num_players')  
    if num_players is None:
        return redirect(url_for('index'))  # If no number of players is set, redirect to index
    
    if request.method == 'POST':
        # Collect player names from the form and store them in the session
        players = [request.form[f'player_{i}'] for i in range(1, num_players + 1)]
        
        # Initialize session with players and other session data
        session['players'] = players  # Save player names in the session
        session['current_player_index'] = 0  # Start with the first player
        session['players_scores'] = {player: 0 for player in players} # Needs python 3.7 or higher.  Otherwise, make an OrderedDict
        
        return redirect(url_for('choose_category'))  # Redirect to the category selection page
    
    return render_template('get_names.html', num_players=num_players)  # Render the names form


# Create a player session
def initialize_player_session(players):
    """Initialize the player session if it's not already set."""
    if 'players' not in session:
        session['players'] = players  # Store the players in the session

    if 'current_player_index' not in session:
        session['current_player_index'] = 0  # Initialize current player index if not set
    
    if 'players_scores' not in session:
        session['players_scores'] = {player: 0 for player in players}  # Initialize player scores

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
    players = session.get('players', []) 
    if not players:
        return redirect(url_for('index'))

    # Create a player session for names and scores
    initialize_player_session(players)

    # Ensure current_player_index is within bounds
    current_player_index = session.get('current_player_index', 0) % len(players)

    # Set the current player
    current_player = players[current_player_index]
    session['current_player'] = current_player

    if request.method == 'POST':
        # Get selected category ID and difficulty
        chosen_category_id = request.form['category']
        difficulty = request.form['difficulty']

        # Redirect to the ask_question page with the selected category ID and difficulty
        return redirect(url_for('ask_question', category=chosen_category_id, difficulty=difficulty))

    return render_template('choose_category.html', 
                            categories=categories, 
                            current_player=current_player)

@app.route('/ask_question', methods=['GET'])
def ask_question():
    # Checks if players exist or not
    players = session.get('players', []) 
    if not players:
        return redirect(url_for('index'))

    # Create a session to hold data between pages
    initialize_player_session(players)
    # Ensure current_player_index is within bounds
    current_player_index = session.get('current_player_index', 0) % len(players)

    # Set the current player
    current_player = players[current_player_index]
    session['current_player'] = current_player

    # Ensure Flask registers session changes
    session.modified = True 

    logger.info(f"Current Player: {current_player} (Index: {current_player_index})")

    # Try to get category and difficulty from request args first, fallback to session
    category = request.args.get('category') or session.get('category')
    difficulty = request.args.get('difficulty') or session.get('difficulty')

    if not category or not difficulty:
        logger.error("Category or difficulty is missing! Redirecting to category selection.")
        return redirect(url_for('choose_category'))  # Redirect if missing

    # Saving just about everything to the session.  I'm not sure what all will be used
    session['category'] = category 
    session['difficulty'] = difficulty

    url = f"https://the-trivia-api.com/v2/questions?categories={category}&difficulty={difficulty}"  

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
                           answers=answers, 
                           current_player=current_player)
    
    except Exception as e:
        logger.error(f"Error fetching question: {str(e)}")
        return f"Error occurred: {str(e)}"
        

@app.route('/answer', methods=['GET', 'POST'])
def answer():
    # In case someone goes directly to the page
    if request.method == ['GET'] :
        return redirect(url_for('index'))
    # Checks if players exist or not
    players = session.get('players', []) 
    if not players:
        return redirect(url_for('index'))        

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
    # Load player scores from session
    players_scores = session.get("players_scores", {})    

    if selected_answer == correctAnswer:
        # Update score if correct
        current_player = session.get("current_player")
        players_scores[current_player] = players_scores.get(current_player, 0) + 1

    # Save updated scores back to session
    session["players_scores"] = {k: players_scores[k] for k in session['players']} 

    # Move to next player and reset automatically when reaching the end
    session['current_player_index'] = (session.get('current_player_index', 0) + 1) % len(session['players'])
    session['current_player'] = session['players'][session['current_player_index']]
    session.modified = True  # Ensure session updates are saved
    current_player = session.get("current_player") # Update this variable to offer next player options

    return render_template('answer.html', 
                           selected_answer=selected_answer, 
                           correctAnswer=correctAnswer,
                           current_player=current_player)

if __name__ == '__main__':
    app.run(debug=True)
