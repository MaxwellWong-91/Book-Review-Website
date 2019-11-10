import os

from flask import Flask, session, render_template, url_for, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

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

# create a user account database
#db.execute('''CREATE TABLE accounts (userId serial, username varchar, password varchar);''')
#db.commit()

#db.execute('''DROP TABLE accounts''')
#db.commit()

#db.execute('''CREATE TABLE reviews (userId int, isbn varchar, rating int, review varchar);''')
#db.commit()

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register")
def registerPage():
    return render_template("register.html")

@app.route("/success", methods = ["POST"])
def registration():
    # get username
    username = request.form.get("username")
   
    # check is username exists already
    if not (db.execute("SELECT username FROM accounts WHERE EXISTS (SELECT username accounts WHERE username = (:username))", {"username": username}).fetchone() is None):   
        return (render_template("failure.html", error = "Failed to create account", message = "This username already exists."))
    # get password
    password = request.form.get("password")
    # check for password length
    if len(password) < 6 or len(password) > 8:
        return (render_template("failure.html", message = "Make sure your password is between 6-8 characters long."))
    
    
    db.execute("INSERT INTO accounts (username, password) VALUES (:username, :password)", 
                        {"username": username, "password": password,})
    db.commit()
    
    
    print(f"username: {username}")
    print(f"password: {password}")
    return (render_template("success.html"))

@app.route("/login")
def loginPage():
    # check if user already logged in
    if session.get("username"):
        return (redirect( url_for("accountPage") ))
  
    return (render_template("login.html"))

@app.route("/account", methods =["GET", "POST"])
def accountPage():
    if (request.method == 'GET' and session.get("username")):
        return (render_template("account.html", username = session.get("username")))

    # get username
    username = request.form.get("username")
    # get password
    password = request.form.get("password")
    
    # check if account credentials match
    if (db.execute("SELECT username, password FROM accounts WHERE EXISTS (SELECT username, password accounts WHERE username = (:username) AND password = (:password))", 
        {"username": username, "password": password}).fetchone() is None):
        return (render_template("failure.html", error = "Failed to login", message = "Make sure your username and password is correct."))
    session["userId"] = db.execute("SELECT userId FROM accounts WHERE username = (:username)", {"username": username}).fetchone()[0]
    session["username"] = db.execute("SELECT username FROM accounts WHERE username = (:username)", {"username": username}).fetchone()[0]
    
    return (render_template("account.html", username = username))

@app.route("/logout")
def logoutPage():
    session.clear()
    
    return (render_template("logout.html"))

@app.route("/found", methods=["POST"])
def searchResult():
    search = request.form.get("search")
    
    
    found = db.execute('''SELECT * FROM books WHERE CONCAT_WS('', isbn, title, author, year) LIKE :search LIMIT 10''', {"search": f"%{search}%"})
    
    """
    index 0: isbn 
    1: title
    2: author
    3: year
    """
    listFound = list(found)
    # check if we find anything
    if len(listFound) == 0:
        return (render_template("failure.html", error = "Search unsuccessful", message = "We were not able to find any books related to your search entry." ))
    return (render_template("found.html", found = listFound))

@app.route("/account/<title>/<isbn>", methods = ["POST", "GET"])
def bookPage(title, isbn):
    # only lets logged in users view this page
    if session.get("username") is None:
        return (render_template("failure.html", error = "Please login", message = "You must be logged in to view this content" ))
    
    # get user id
    userId = session.get("userId")
    
    print (userId)
    # get the review
    review = db.execute('''SELECT rating, review FROM reviews WHERE userId = (:userId) AND isbn = (:isbn)''', {"userId": userId, "isbn": isbn} ).fetchone()
    if review is None:
        review = []
    else:
        review = list(review)

    # if someone just submit a review
    if request.method == "POST" and len(review) == 0 and len(request.form.get("review")) < 400:
        db.execute("INSERT INTO reviews (userId, isbn, rating, review) VALUES (:userId, :isbn, :rating, :review)",
                   {"userId": userId, "isbn": isbn, "rating": request.form.get("rating"), "review": request.form.get("review")})
        db.commit()

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "HJOvd2AhDAvuwjhlhbg", "isbns": isbn})
    # check if api call returns
    if (res.status_code != 200):
        return (render_template("failure.html", error = "API call unsuccessful", message = "We were unable to find book reviews from goodreads."))
    data = res.json()
    
    # get the review
    review = db.execute('''SELECT rating, review FROM reviews WHERE userId = (:userId) AND isbn = (:isbn)''', {"userId": userId, "isbn": isbn} ).fetchone()
    if review is None:
        review = []
    else:
        review = list(review)

    
    
    return (render_template("bookReview.html", title = title, isbn = isbn,
                            averageRating = data.get("books")[0].get("average_rating"), 
                            totalReviews = data.get("books")[0].get("work_ratings_count"), 
                            review = review))

@app.route("/api/<isbn>")
def bookApi(isbn):
    data = db.execute('''SELECT title, author, year FROM books WHERE isbn = (:isbn)''', {"isbn": isbn}).fetchone()
    # returns error if book no in database
    if data is None:
        return jsonify({"error": "We were unable to find this book"}), 404

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "123", "isbns": isbn})
    # check if call returns
    if (res.status_code != 200):
        return jsonify({"error": "We were unable to find reviews for this book"}), 404
    print (res)
    print (type(res))
    res = res.json()
   
    return jsonify( {"title": data[0],
                     "author": data[1],
                     "year": data[2],
                     "isbn": isbn,
                     "review_count": res.get("books")[0].get("work_ratings_count"),
                     "average_score": res.get("books")[0].get("average_rating")})
if __name__ == '__main__':
    app.debug = True
    app.run()
