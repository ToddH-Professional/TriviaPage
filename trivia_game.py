from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management

@app.route('/', methods=['GET', 'POST'])
def start_game():
    if request.method == 'POST':
        # Get the number of players from the form and save it in session
        num_players = int(request.form['num_players'])
        session['num_players'] = num_players  # Store the number of players in the session
        return redirect(url_for('get_names'))  # Redirect to next step to get names
    
    return render_template('index.html')  # Render the initial page with the form

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


if __name__ == '__main__':
    app.run(debug=True)
