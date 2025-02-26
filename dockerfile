# Use a base image with Python installed
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app into the container
COPY . .

# Expose the port the app runs on (default is 5000 for Flask)
EXPOSE 5000

# Set the command to run the app
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--log-level", "debug", "trivia_game:app"]
