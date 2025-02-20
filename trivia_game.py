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

if __name__ == '__main__':
    app.run(debug=True)
