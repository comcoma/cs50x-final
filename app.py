import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, dateformat

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Connect to DB
db = SQL("sqlite:///cloud.db")

# Date formatter
""" Jinja Filter """
app.jinja_env.filters["dateformat"] = dateformat


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Show all the ideas posted"""
    rows = db.execute("SELECT * FROM ideas ORDER BY votes DESC")
    users = ''
    if session.get("user_id") is not None:
        users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    return render_template("index.html", rows=rows, users=users)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id (can't do that if i want to flash a message and reload, because it clears flash message)
    #session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please, enter your username", 'warning')
            return redirect("/login")

        # Ensure password was submitted
        if not request.form.get("password"):
            flash("Please, enter your password", 'warning')
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password", 'error')
            return redirect("/login")

        # Remember which user has logged in
        try:
            session["user_id"] = rows[0]["id"]
        except:
            flash("User not found", 'error')
            return redirect("/login")

        # Redirect user to home page
        flash("Logged in!", 'info')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id and redirect to home
    session.clear()
    flash("Logged out!", 'info')
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    #session.clear() (cant do that if i want to use flash messages)
    # User reached route via POST (submitting the register form)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            flash("Please, enter a username", 'warning')
            return redirect("/register")

        # ensure password was submitted
        elif not request.form.get("password"):
            flash("Please, enter a password", 'warning')
            return redirect("/register")

        # ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords do not match", 'warning')
            return redirect("/register")

        # save username and password hash in variables
        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"))

        # Query database to ensure username isn't already taken
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=username)
        if len(rows) != 0:
            flash("Username is already taken", 'warning')
            return redirect("/register")

        # insert username and hash into database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                   username=username, hash=hash)

        # redirect to login page
        flash("Successfully registered", 'warning')
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """ Add new idea"""
    if request.method == "GET":
        categories = db.execute("SELECT category,id FROM categories")
        # Load new idea form
        users = ''
        if session.get("user_id") is not None:
            users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        return render_template("add.html", categories=categories, users=users)
    else:
        author_id = session["user_id"]
        title = request.form.get("title")
        category_id = request.form.get("category_id")
        img = request.form.get("img")
        description = request.form.get("description")

        # ensure title was provided
        if not request.form.get("title"):
            flash("Please, enter a title", 'warning')
            return redirect("/add")
        # ensure description was provided
        elif not request.form.get("description"):
            flash("Please, enter a description", 'warning')
            return redirect("/add")
        # ensure img URL was provided
        elif not request.form.get("img"):
            flash("Please, enter a img URL", 'warning')
            return redirect("/add")
        # ensure category is selected
        elif not request.form.get("category_id"):
            flash("Please, select a category", 'warning')
            return redirect("/add")
        else:
            db.execute("INSERT INTO ideas (author_id, title, description, img) VALUES(?,?,?,?)", author_id, title, description, img)

        return redirect("/")

@app.route("/vote", methods=["GET", "POST"])
@login_required
def vote():
    """ Add an idea to favourites / vote """
    if request.method == "GET":
        # Load new idea form
        return redirect("/")
    else:
        idea_id = request.form.get("idea_number_field")
        user_id = session["user_id"]
        
        # check if already voted for that idea
        rows = db.execute("SELECT * FROM favs WHERE idea_id = ? AND user_id = ?", idea_id, user_id)
        if len(rows) == 1:
            # remove vote in this case
            db.execute("DELETE FROM favs WHERE idea_id = ? AND user_id = ?", idea_id, user_id)
            # decrease votes by 1
            db.execute("UPDATE ideas SET votes = votes - 1 WHERE idea_id = ?", idea_id)
            flash("Removed from favourites", 'warning')
            return redirect("/")

        # ensure increase vote count by 1
        db.execute("UPDATE ideas SET votes = votes + 1 WHERE idea_id = ?", idea_id)

        db.execute("INSERT INTO favs('idea_id', 'user_id') VALUES (?,?)", idea_id, user_id)
        
        flash("Thanks for voting", 'warning')
        return redirect("/")

@app.route("/my_ideas")
@login_required
def my_ideas():
    """Show all the ideas posted by me"""
    author_id = session["user_id"]
    rows = db.execute("SELECT * FROM ideas WHERE author_id = ? ORDER BY votes DESC", author_id)
    
    users = ''
    editing = True
    if session.get("user_id") is not None:
        users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    return render_template("index.html", rows=rows, users=users, editing=editing)

@app.route("/favorites")
@login_required
def favorites():
    """Show favorites I voted for"""
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM ideas JOIN favs ON favs.idea_id = ideas.idea_id WHERE user_id = ? ORDER BY votes", user_id)
    
    users = ''
    if session.get("user_id") is not None:
        users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    return render_template("index.html", rows=rows, users=users)

@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """Delete my idea"""
    if request.method == "GET":
        # Load new idea form
        return redirect("/")
    else:
        idea_id = request.form.get("idea_number_field")
        user_id = session["user_id"]
        author_id = db.execute("SELECT author_id FROM ideas WHERE idea_id = ? ", idea_id)
        author_num = author_id[0]['author_id']

        if int(author_num) == int(user_id):
            db.execute("DELETE FROM ideas WHERE idea_id = ?", idea_id)
            flash("Your idea was deleted", 'warning')
            return redirect("/")
        else:
            flash("You tried to delete someone else's idea", 'warning')
            return redirect("/")