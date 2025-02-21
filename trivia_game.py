from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import html
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management

@app.route('/', methods=['GET', 'POST'])
def start_game():
    if request.method == 'POST':
        # Get the number of players from the form
        num_players = int(request.form['num_players'])
        session['num_players'] = num_players  # Save number of players in session
        return redirect(url_for('get_names'))  # Go to the next step (get names)
    
    return render_template('index.html')  # Render start game page

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
    # Fetch categories from the trivia API
    url = "https://opentdb.com/api_category.php"
    response = requests.get(url)
    categories = response.json().get('trivia_categories', [])

    if request.method == 'POST':
        # Get the chosen category and difficulty
        chosen_category = request.form['category']
        difficulty = request.form['difficulty']

        # Redirect to the next step to fetch questions based on the chosen category and difficulty
        return redirect(url_for('ask_question', category=chosen_category, difficulty=difficulty))

    return render_template('choose_category.html', categories=categories)  # Render the category selection page

@app.route('/ask_question', methods=['GET', 'POST'])
def ask_question():
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')

    # Fetch a question based on the selected category and difficulty
    url = f"https://opentdb.com/api.php?amount=1&category={category}&difficulty={difficulty}&type=multiple"
    response = requests.get(url)

    # Check if response is valid
    if response.status_code != 200:
        return "Error fetching questions. Please try again later."

    # Output the raw JSON body for debugging
    json_data = response.json()
    return f"<pre>{json.dumps(json_data, indent=2)}</pre>"  # Pretty-print the JSON response


if __name__ == '__main__':
    app.run(debug=True)
