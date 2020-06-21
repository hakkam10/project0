import os

from flask import Flask, render_template, request, session, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods = ["GET", "POST"])
def index():
    if 'username' in session:
        session.pop('username',None)
        return render_template("index.html")

    return render_template("index.html")

@app.route("/registered", methods=["POST"])
def registered():

    """update user"""
    # get user information
    try:
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
    except ValueError:
        return render_template("error.html", message="Invalid name or user name.")

    #update users
    db.execute("INSERT INTO users (name, username, password) VALUES (:name, :username, :password)",
            {"name": name, "username": username, "password": password})
    db.commit()
    return render_template("registered.html")

@app.route("/search", methods=["POST"])
def search():
    # get login information
    username = request.form.get("username")
    password = request.form.get("password")
    name = db.execute("SELECT name FROM users WHERE (username = :username) AND (password = :password)",
                        {"username": username, "password": password})
    # invalid
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).rowcount == 0:
        return render_template("error.html", message="Invalid username or password")
    #valid
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).rowcount == 1:
        session["username"] = [username]
        return render_template("search.html", name=name)

@app.route("/result", methods=["POST"])
def results():
    search = request.form.get("search")
    # get search keywords
    books = db.execute("SELECT * FROM books1 WHERE isbn ILIKE :search OR title ILIKE :search OR author ILIKE :search", {"search": search}).fetchall()

    return render_template("results.html", books=books, rating="3.5")


@app.route("/book")
def book():
    return render_template("book.html")
