from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import html
import time
import logging

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

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Adjust the level as necessary

# Set up logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/ask_question', methods=['GET', 'POST'])
def ask_question():
    category = request.args.get('category', '9')  # Default to General Knowledge if no category
    difficulty = request.args.get('difficulty', 'easy')  # Default to easy if no difficulty

    # Define retry parameters
    max_retries = 5
    retry_delay = 2  # Seconds to wait between retries
    attempt = 0
    question_data = None

    # Try fetching the question with retries
    while attempt < max_retries:
        try:
            url = f"https://opentdb.com/api.php?amount=1&category={category}&difficulty={difficulty}&type=multiple"
            response = requests.get(url)

            # Handle rate limiting (429 Too Many Requests)
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 5)  # Default to 5 seconds
                logging.warning(f"Rate limit exceeded, retrying after {retry_after} seconds.")
                time.sleep(int(retry_after))  # Wait before retrying
                attempt += 1
                continue

            # Log the API response to see what data we're receiving
            logging.debug(f"API Response: {response.json()}")

            # If we get a valid response, break the retry loop
            question_data = response.json().get('results', [])
            if question_data:
                question_data = question_data[0]  # Get the first question
                break

        except (requests.exceptions.RequestException, IndexError) as e:
            attempt += 1
            logging.error(f"Error fetching question, attempt {attempt} of {max_retries}: {e}")
            time.sleep(retry_delay)  # Wait before retrying

    if not question_data:
        return "Sorry, there was an error fetching a question. Please try again later."

    # Extract question details
    question = question_data['question']
    correct_answer = question_data['correct_answer']
    options = question_data['incorrect_answers']
    options.append(correct_answer)  # Add the correct answer
    random.shuffle(options)  # Shuffle the options

    # Decode any HTML entities in the question text and answers
    question = html.unescape(question)
    options = [html.unescape(option) for option in options]
    correct_answer = html.unescape(correct_answer)  # Also unescape the correct answer

    # Store question data temporarily (in session)
    session['current_question'] = {
        'question': question,
        'correct_answer': correct_answer,
        'options': options
    }

    return render_template('ask_question.html', question=question, options=options)


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
