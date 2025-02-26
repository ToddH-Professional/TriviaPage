from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import html
import time
import logging
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the players' scores and names
players_scores = {}
player_order = []  # To store the order of players
current_player_index = 0

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        num_players = int(request.form['num_players'])  # Get number of players from the form
        session['num_players'] = num_players  # Store the number of players in the session
        return redirect(url_for('get_names'))  # Redirect to the player names page
    
    return render_template('index.html')  # Render the index page if it's a GET request


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

# fetch_categories with logging
def fetch_categories():
    url = 'https://opentdb.com/api_category.php'
    logger.info(f"Requesting category data from {url}")
    
    try:
        response = requests.get(url)
        logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code} | Headers: {dict(response.request.headers)}")
        # If rate limit is exceeded
        if response.status_code == 429:
            time.sleep(5)  # Wait for 5 seconds
            # Retry the request after waiting
            response = requests.get(url)
            logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code} | Headers: {dict(response.request.headers)}")

        # If successful, process the category data
        if response.status_code == 200:
            logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code} | Headers: {dict(response.request.headers)}")
            data = response.json()
            categories = data.get('trivia_categories', [])
            if categories:
                logger.info(f"Received {len(categories)} categories.")
                desired_categories = ['General Knowledge', 'Sports', 'Geography', 'History', 'Art', 'Science & Nature']
                categories = [cat for cat in categories if cat['name'] in desired_categories]
                return categories
            else:
                logger.error("No categories found in the response.")
                return []

        else:
            logger.error(f"Failed to fetch categories. Status code: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return []
    
@app.route('/choose_category', methods=['GET', 'POST'])
def choose_category():
    categories = fetch_categories()       
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

    url = f"https://opentdb.com/api.php?amount=1&category={category}&difficulty={difficulty}&type=multiple"   

    # Pulls the question and answers
    try:
        response = requests.get(url)
        # Log the request details after the GET request
        logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code} | Headers: {dict(response.request.headers)}")
        # For timed retries.  When it returns 429 wait 5 seconds which is their rate limit
        if response.status_code == 429:
            time.sleep(5)
            response = requests.get(url)
            # Log the request details for the retry
            logger.info(f"Request: {response.request.method} {response.url} | Status_Code: {response.status_code}")
        # Here is what happens after success
        if response.status_code == 200:
            question_data = response.json().get('results', [])[0]
            # Unescape text
            question_data['question'] = html.unescape(question_data['question'])
            question_data['correct_answer'] = html.unescape(question_data['correct_answer']) 
            question_data['incorrect_answers'] = [html.unescape(answer) for answer in question_data['incorrect_answers']] 
            # Answers get saved
            answers = question_data['incorrect_answers'] + [question_data['correct_answer']]
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
    logger.info(f"Session data at /answer: {json.dumps(session, indent=4)}")
    question = session.get('question')
    if not question:
        logger.error("No question found in session!")
        return redirect(url_for('ask_question'))  # Redirect to fetch a new question

    correct_answer = question.get('correct_answer')    
    # Load player scores from session
    players_scores = session.get("players_scores", {})    

    if selected_answer == correct_answer:
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
                           correct_answer=correct_answer,
                           current_player=current_player)

if __name__ == '__main__':
    app.run(debug=True)
