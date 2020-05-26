import os
import requests

from flask import Flask, session, render_template, request, url_for, redirect, jsonify
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
def login():
    session["loggedIn"] = False
    if(request.method == "POST"):      
        username = request.form.get("loginname")
        password = request.form.get("loginpass")
        if (db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).rowcount == 0):
            return render_template("login.html", message = "Invalid Username")
        users = db.execute("SELECT password, id FROM users WHERE username = :username", {"username":username})
        userPassword = ""
        id = 0
        for user in users:
            userPassword = user.password
            id = user.id
        if(userPassword != password):
            return render_template("login.html", message = "Wrong Password")
        session["loggedIn"] = True
        session["user_id"]  = id
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
    session["loggedIn"] = False
    if(request.method == "POST"):
        first = request.form.get("first")
        last = request.form.get("last")
        username = request.form.get("username")
        password = request.form.get("password")
        db.execute("INSERT INTO users (first, last, username, password) VALUES (:first, :last, :username, :password)",
        {"first": first, "last": last, "username": username, "password": password, })
        db.commit()
        print(f"Hello {first} {last}: {username} : {password} ")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/home", methods = [ "GET", "POST"] )
def index():
    if session["loggedIn"]:
        if(request.method == "POST"):
            title = request.form.get("title")
            if(title != ""):
                title = '%' + title + '%'
            author = request.form.get("author")
            if(author != ""):
                author = '%' + author + '%'
            isbn = request.form.get("isbn")
            if(isbn != ""):
                isbn = '%' + isbn + '%'
            books = None
            print(title + " " + author + " " + isbn )
            if(isbn != ""):
                books = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": isbn})
            else: 
                if(title == "" and author != ""):
                    books = db.execute("SELECT * FROM books WHERE LOWER(author) LIKE LOWER(:author)", 
                    { "author": author})
                elif(author == "" and title != ""):
                    books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:title)", 
                    { "title": title})
                elif(author != "" and title != ""): 
                    books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:title) AND LOWER(author) LIKE LOWER(:author)", 
                    {"title": title, "author": author})
            if (books == None or books.rowcount == 0):
                return render_template("index.html", message = "No Matches")
            else:
                return render_template("index.html", books = books)
        return render_template("index.html")
    return redirect(url_for('login'))

@app.route("/home/<isbn>", methods = ["GET", "POST"])
def books(isbn):
    
    if (db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).rowcount == 0):
       return redirect(url_for('index'))
    books = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn})
    title = ""
    author = ""
    year = ""
    key = "VZgJ3pdMB6ROE02lQv2w"
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":key, "isbns":isbn})
    data = res.json()
    avg_rating = data["books"][0]["average_rating"]
    for book in books:
       title = book.title
       author = book.author
       year = book.year
    if(request.method == "POST"):
        review = request.form.get("review")
        rating = request.form.get("rating")
        print(rating + " " + review)
        alreadyReviewed = False
        previousReviews = db.execute("SELECT user_id  from reviews WHERE isbn = :isbn", {"isbn":isbn})
        for eachreview in previousReviews:
            if(eachreview.user_id == session["user_id"] and alreadyReviewed == False):
                alreadyReviewed = True
        if (alreadyReviewed == True):
            reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn})
            return render_template("bookpage.html", title = title, author = author, year = year, reviews = reviews, avg_rating = avg_rating, message = "Can only submit 1 review per book")
        else:
            db.execute("INSERT INTO reviews (review, rating, user_id, isbn) VALUES (:review, :rating, :user_id, :isbn)",
            {"review" : review, "rating":rating, "user_id" : session["user_id"], "isbn":isbn})
            db.commit()
            reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn})
            return render_template("bookpage.html", title = title, author = author, year = year, reviews = reviews, avg_rating = avg_rating)
    if(request.method == "GET"):
        reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn})
        return render_template("bookpage.html", title = title, author = author, year = year, reviews = reviews, avg_rating= avg_rating)
    
@app.route("/api/<isbn>", methods = ["GET"])
def api(isbn):
    books = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn})
    if(books.rowcount == 0):
        return "404 invalid isbn"
    title = ""
    author = ""
    year = ""
    
    key = "VZgJ3pdMB6ROE02lQv2w"
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":key, "isbns":isbn})
    data = res.json()
    avg_rating = data["books"][0]["average_rating"]

    for book in books:
        title = book.title
        author = book.author
        year = book.year

    return jsonify(
        title = title,
        author = author,
        year = year,
        avg_rating = avg_rating,
        isbn = isbn)

