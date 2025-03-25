# Trivia App

https://triviapage-triviapage.up.railway.app

A fun and interactive trivia game that you can play solo! This app is built using Flask and integrates with an external trivia API to generate questions. It supports player tracking, scoring, and a category-based question selection system.

## Features

- Single-player trivia game
- Category and difficulty selection
- Score tracking
- Google authentication for login
- Deployed using Docker and Kubernetes

## Requirements

- Python 3.9+
- Flask
- PostgreSQL
- Docker
- Kubernetes
- Railway for deployment
- Trivia API access

## Installation

1. **Clone the Repository**

   ```sh
   git clone https://github.com/ToddH-Professional/TriviaPage.git
   ```
   1. **Create a .env file for a couple variable
   ```sh
   FLASK_SECRET_KEY=""
   DATABASE_PUBLIC_URL="postgresql://postgres:postgres@db:5432/triviagame_db" 
   ```


## Running with Docker

1. **Build the Docker Image**

   ```sh
   docker build -f .\dockerfile.dev -t trivia-web-app:dev .
   ```

2. **Run the Container**

   ```sh
   docker-compose up -d --build
   ```

## Database Setup

- The app uses PostgreSQL for storing game sessions and player data.  For the deployed version, it uses a Railway DB

## API Integration

- Trivia questions are fetched from an external trivia API.
- API calls are rate-limited (one request per 5 seconds).

## Future Enhancements

- Multiplayer mode
- WebSockets for real-time gameplay
- Enhanced UI/UX

## License

This project is licensed under the MIT License.

