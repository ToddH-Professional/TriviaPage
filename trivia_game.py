from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import html
import time
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management

# Initialize the players' scores and names
players_scores = {}
player_order = []  # To store the order of players
current_player_index = 0

@app.route('/', methods=['GET', 'POST'])
def start_game():
    # If the form is submitted, we add the players and redirect to the category selection page
    if request.method == 'POST':
        num_players = int(request.form['num_players'])
        for i in range(num_players):
            player_name = request.form[f'player_name_{i+1}']
            players.append(player_name)
            scores[player_name] = 0  # Initialize their score
        return redirect(url_for('choose_category'))  # Redirect to the category selection

    return render_template('start_game.html')  # Render the start game page

@app.route('/get_names', methods=['GET', 'POST'])
def get_names():
    num_players = session.get('num_players')  # Get the number of players from the session
    if num_players is None:
        return redirect(url_for('start_game'))  # If num_players is not found, go back to start
    
    if request.method == 'POST':
        # Collect player names and store them in the session
        players = [request.form[f'player_{i}'] for i in range(1, num_players + 1)]
        session['players'] = players  # Save the list of players' names in the session
        return redirect(url_for('choose_category'))  # Redirect to the next step (choose category)
    
    return render_template('get_names.html', num_players=num_players)  # Render the player names form

@app.route('/choose_category', methods=['GET', 'POST'])
def choose_category():
    # Simulate category selection (In real app, you'd fetch categories from an API)
    categories = ['General Knowledge', 'Science', 'History', 'Sports']

    # Get the current player’s turn
    current_player_name = players[current_player_index]

    if request.method == 'POST':
        # Get selected category and difficulty
        chosen_category = request.form['category']
        difficulty = request.form['difficulty']
        
        # Redirect to the ask_question page with the category and difficulty selected
        return redirect(url_for('ask_question', category=chosen_category, difficulty=difficulty))

    return render_template('choose_category.html', categories=categories, current_player_name=current_player_name)

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Adjust the level as necessary

@app.route('/ask_question', methods=['GET', 'POST'])
def ask_question():
    global current_player_index

    category = request.args.get('category')
    difficulty = request.args.get('difficulty')

    current_player = player_order[current_player_index]
    
    # Fetch a question based on the selected category and difficulty
    url = f"https://opentdb.com/api.php?amount=1&category={category}&difficulty={difficulty}&type=multiple"
    response = requests.get(url)
    question_data = response.json().get('results', [])[0]

    if not question_data:
        return "No question found, try again!"

    # Unescape the question and answer options
    question = html.unescape(question_data['question'])
    correct_answer = html.unescape(question_data['correct_answer'])
    options = [html.unescape(answer) for answer in question_data['incorrect_answers']]
    options.append(correct_answer)  # Add the correct answer
    random.shuffle(options)  # Shuffle the options

    # Handle POST request (when user submits an answer)
    if request.method == 'POST':
        selected_answer = request.form['answer']
        if selected_answer == correct_answer:
            players_scores[current_player] += 1  # Increment score for correct answer

        # Get the next player for the next turn
        current_player_index = (current_player_index + 1) % len(player_order)  # Loop through players
        return redirect(url_for('ask_question', category=category, difficulty=difficulty))

    return render_template('ask_question.html', question=question, options=options, current_player=current_player, score=players_scores[current_player])

def get_next_player(current_player):
    player_list = list(players_scores.keys())
    current_index = player_list.index(current_player)
    next_index = (current_index + 1) % len(player_list)  # Loop back to first player after last player
    return player_list[next_index]

@app.route('/answer', methods=['POST'])
def answer():
    # Retrieve stored question data from session
    current_question = session.get('current_question')
    if not current_question:
        return "No question found in session."

    correct_answer = current_question['correct_answer']
    selected_answer = request.form['answer']

    if selected_answer == correct_answer:
        result_message = "Congratulations, you got the answer right!"
    else:
        result_message = f"Too bad! The correct answer was: {correct_answer}"

    # Show the result page
    return render_template('result.html', result_message=result_message, correct_answer=correct_answer)

if __name__ == '__main__':
    app.run(debug=True)
