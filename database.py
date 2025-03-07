# database.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash

# Create a SQLAlchemy instance
db = SQLAlchemy()
bcrypt = Bcrypt()

# Define the Player model
class User(UserMixin, db.Model):  # UserMixin helps with login functionality
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Store hashed password
    score = db.Column(db.Integer, default=0)

    def set_password(self, password):
        """Hash and set the password using bcrypt"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verify the password using bcrypt"""
        return bcrypt.check_password_hash(self.password_hash, password)
