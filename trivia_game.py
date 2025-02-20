from flask import Flask, render_template, jsonify
import requests
import random
import html
import os

app = Flask(__name__)

def fetch_trivia():
    url = "https://opentdb.com/api.php?amount=1&type=multiple"
    response = requests.get(url)
    response.raise_for_status()
    trivia_data = response.json()
    
    if trivia_data["response_code"] == 0:
        question_data = trivia_data["results"][0]
        question = html.unescape(question_data["question"])
        correct_answer = html.unescape(question_data["correct_answer"])
        all_answers = [html.unescape(ans) for ans in question_data["incorrect_answers"]] + [correct_answer]
        random.shuffle(all_answers)
        
        return {
            "question": question,
            "choices": all_answers,
            "answer": correct_answer
        }
    return None

@app.route('/')
def index():
    trivia = fetch_trivia()
    return render_template('index.html', trivia=trivia)

@app.route('/get_trivia')
def get_trivia():
    trivia = fetch_trivia()
    return jsonify(trivia)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
