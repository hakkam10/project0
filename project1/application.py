import os, requests

from flask import Flask, render_template, request, session, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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
    #Logout
    if 'username' in session:
        session.pop('username', None)
        return render_template("index.html")

    return render_template("index.html")

@app.route("/register", methods=["POST"])
def registered():

    """update user"""
    # get user information
    try:
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
    except IntegrityError as Error:
        return render_template("index.html", message_signup="Username already exists.")
    except ValueError:
        return render_template("index.html", message_signup="Invalid name or user name.")

    #update users
    db.execute("INSERT INTO users (name, username, password) VALUES (:name, :username, :password)",
            {"name": name, "username": username, "password": password})
    db.commit()
    return render_template("registered.html")

@app.route("/search", methods=["POST", "GET"])
def search():
    # get login information
    username = request.form.get("username")
    password = request.form.get("password")
    session["username"] = username
    # invalid
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).rowcount == 0:
        return render_template("index.html", message_login="Invalid username or password")

    #valid
    if db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).rowcount == 1:
        user = db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", {"username": username, "password": password}).fetchone()[1]
        return render_template("search.html", user=user)

    if request.method == "GET":
        try:
            user = db.execute("SELECT * FROM users WHERE username = :username", {"username": session["username"]}).fetchone()[1]
            return render_template("search.html", user=user)
        except KeyError:
            return render_template("error.html", message="Login to continue")
        except TypeError:
            return render_template("error.html", message="Login to continue")

@app.route("/results", methods=["POST"])
def results():
    query = request.form.get("search")
    search = "%" + query + "%"
    # get search keywords
    books = db.execute("SELECT * FROM books WHERE (isbn ILIKE :search OR title ILIKE :search OR author ILIKE :search)", {"search": search}).fetchall()

    return render_template("results.html", books=books, search=query)


@app.route("/book/<string:isbn>")
def book(isbn):
    # Information about book
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3rPbVPJrIXkzd5UMgDQnHw", "isbns": isbn})
    comments = db.execute("SELECT * FROM review WHERE isbn = :isbn ORDER BY id DESC", {"isbn": isbn})
    avg = db.execute("SELECT ROUND(AVG(star), 2) FROM rating WHERE isbn = :isbn", {"isbn": isbn}).fetchall()[0][0]
    no_of_rating = db.execute("SELECT COUNT(star) FROM rating WHERE isbn = :isbn", {"isbn": isbn}).fetchone()[0]

    try:
        user = db.execute("SELECT * FROM users WHERE username = :username", {"username": session["username"]}).fetchone()[1]
        data = res.json()
        ratings = data["books"][0]["average_rating"]
        work_ratings = data["books"][0]["work_ratings_count"]
        return render_template("book.html", book=book, ratings=ratings, work_ratings=work_ratings, avgstars=avg, no_of_rating=no_of_rating, comments=comments)
    except ValueError:
        return render_template("book.html", book=book, ratings="(json request failed)", work_ratings="(json request failed)", avgstars=avg, no_of_rating=no_of_rating, comments=comments)
    except KeyError:
        return render_template("error.html", message="Login to continue")
    except TypeError:
        return render_template("error.html", message="Login to continue")



@app.route("/book/<string:isbn>", methods=["POST", "GET"])
def submitr(isbn):
    # Information about book
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3rPbVPJrIXkzd5UMgDQnHw", "isbns": isbn})
    data = res.json()
    ratings = data["books"][0]["average_rating"]
    work_ratings = data["books"][0]["work_ratings_count"]
    comments = db.execute("SELECT * FROM review WHERE isbn = :isbn ORDER BY id DESC", {"isbn": isbn})
    avg = db.execute("SELECT ROUND(AVG(star), 2) FROM rating WHERE isbn = :isbn", {"isbn": isbn}).fetchall()[0][0]
    no_of_rating = db.execute("SELECT COUNT(star) FROM rating WHERE isbn = :isbn", {"isbn": isbn}).fetchone()[0]
    # rating and review
    if request.method == "POST":
        star = request.form.get("star")
        comment = request.form.get("comment")
    # for rating
        if star:
            try:
                db.execute("INSERT INTO rating (username, star, isbn) VALUES (:username, :star, :isbn)", {"username": session["username"], "star": star, "isbn": isbn})
                db.commit()
                return render_template("book.html", book=book, ratings=ratings, comments=comments, avgstars=avg, no_of_rating=no_of_rating, work_ratings=work_ratings, reviewstars="", reviewtext="", messagecomment="", messagestar="Rating submitted")
            except IntegrityError as Error:
                return render_template("book.html", book=book, ratings=ratings, comments=comments, avgstars=avg, no_of_rating=no_of_rating, work_ratings=work_ratings, reviewstars="", reviewtext="", messagecomment="", messagestar="You have already rated")
            except KeyError:
                return render_template("error.html", message="Login to continue")
        # for review
        if comment:
            try:
                db.execute("INSERT INTO review (username, comment, isbn) VALUES (:username, :comment, :isbn)", {"username": session["username"], "comment": comment, "isbn": isbn})
                db.commit()
                return render_template("book.html", book=book, ratings=ratings, comments=comments, avgstars=avg, no_of_rating=no_of_rating, work_ratings=work_ratings, reviewstars="", reviewtext="", messagestar="", messagecomment="Review submitted")
            except IntegrityError as Error:
                return render_template("book.html", book=book, ratings=ratings, comments=comments, avgstars=avg, no_of_rating=no_of_rating, work_ratings=work_ratings, reviewstars="", reviewtext="", messagestar="", messagecomment="You have already submitted your review")
            except KeyError:
                return render_template("error.html", message="Login to continue")

    if request.method == "GET":
        return render_template("book.html", book=book, ratings=ratings, comments=comments, avgstars=avg, no_of_rating=no_of_rating, work_ratings=work_ratings, reviewstars="", reviewtext="", messagestar="", messagecomment="")

@app.route("/home", methods=["POST", "GET"])
def home():
    try:
        user = db.execute("SELECT * FROM users WHERE username = :username", {"username": session["username"]}).fetchone()[1]
        return render_template("search.html", user=user)
    except KeyError:
        return render_template("error.html", message="Login to continue")

@app.route("/api/<string:isbn>", methods = ["GET"])
def api(isbn):
    # make sure book exists
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if book is None:
        return jsonify ({"error": "invalid isbn"}), 422

    # information about books
    avg = str(db.execute("SELECT ROUND(AVG(star), 2) FROM rating WHERE isbn = :isbn", {"isbn": isbn}).fetchall()[0][0])
    no_of_rating = db.execute("SELECT COUNT(star) FROM rating WHERE isbn = :isbn", {"isbn": isbn}).fetchone()[0]
    no_of_review = db.execute("SELECT COUNT(comment) FROM review WHERE isbn = :isbn", {"isbn": isbn}).fetchone()[0]

    return jsonify({
    "title": book.title,
    "author": book.author,
    "year": book.year,
    "isbn": book.isbn,
    "review_count": no_of_rating,
    "rating_count": no_of_review,
    "average_score": avg
    })
