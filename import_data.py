import psycopg2
import json
import requests  # Use `requests` to pull data from a remote source

# init_db.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define your database URL (use environment variable or hardcode for now)
DATABASE_URL = 'postgresql://postgres:password@localhost:5432/mydb'

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define a simple table for demo purposes
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String)

# Create the table in the database
Base.metadata.create_all(engine)

# Add some initial data
Session = sessionmaker(bind=engine)
session = Session()

# Check if data already exists, else add some
if not session.query(User).first():
    user = User(username='johndoe', email='john@example.com')
    session.add(user)
    session.commit()

session.close()
