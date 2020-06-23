import os, requests

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
    # invalid
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).rowcount == 0:
        return render_template("error.html", message="Invalid username or password")

    #valid
    user = db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).fetchone()
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).rowcount == 1:
        session["username"] = username
        return render_template("search.html", user=user)

@app.route("/results", methods=["POST"])
def results():
    search = "%" + request.form.get("search") + "%"
    # get search keywords
    books = db.execute("SELECT * FROM books1 WHERE (isbn ILIKE :search OR title ILIKE :search OR author ILIKE :search)", {"search": search}).fetchall()
    for book in books:
        isbn = book.isbn
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3rPbVPJrIXkzd5UMgDQnHw", "isbns": isbn})
    data = res.json()
    ratings = data["books"][0]["average_rating"]

    return render_template("results.html", books=books, rating=ratings, search=search)


@app.route("/book/<string:isbn>")
def book(isbn):
    book = db.execute("SELECT * FROM books1 WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3rPbVPJrIXkzd5UMgDQnHw", "isbns": isbn})
    data = res.json()
    ratings = data["books"][0]["average_rating"]
    work_ratings = data["books"][0]["work_ratings_count"]
    return render_template("book.html", book=book, ratings=ratings, work_ratings=work_ratings, reviewstars="", reviewtext="")
