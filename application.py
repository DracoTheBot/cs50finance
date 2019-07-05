import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    zero=0
    rows = db.execute("SELECT * FROM stocks WHERE user_id = :Id AND shares != :zero", Id=session["user_id"], zero=zero)
    rowCount = db.execute("SELECT count(*) FROM stocks WHERE user_id = :Id AND shares != :zero", Id=session["user_id"], zero=zero)
    end = len(rows)
    userCash = db.execute("SELECT cash FROM users WHERE id = :Id", Id=session["user_id"])
    listcash = float(userCash[0]["cash"])
    cash=usd(listcash)
    twod_list = []
    grandtotal = 0
    for i in range(rowCount[0]["count(*)"]):
        new = []
        for j in range(5):
            newdic=lookup(rows[i]["symbol"])
            if j == 0:
                new.append(rows[i]["symbol"])
            elif j == 1:
                newdic=lookup(rows[i]["symbol"])
                new.append(newdic["name"])
            elif j == 2:
                new.append(rows[i]["shares"])
            elif j == 3:
                new.append(usd(newdic["price"]))
            else:
                total=float(newdic["price"]) * float(rows[i]["shares"])
                new.append(usd(total))
        twod_list.append(new)
        grandtotal = grandtotal+total
    grandtotal = grandtotal+listcash
    grandtotal = usd(grandtotal)
    return render_template("index.html", grandtotal=grandtotal, cash=cash, rowCount=rowCount, twod_list=twod_list)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        symbol=symbol.upper()
        if lookup(symbol) == None or not request.form.get("symbol"):
            return apology("please input a correct symbol")
        row = db.execute("SELECT * FROM users WHERE id= :Id", Id = session["user_id"])
        currentCash = row[0]["cash"]
        diction = lookup(symbol)
        shareMultiple = int(request.form.get("shares"))
        symbolCash = diction["price"] * shareMultiple
        if currentCash < symbolCash:
            return apology("Not enough Money")
        else: 
            currentCash = currentCash - symbolCash
            db.execute("UPDATE users SET cash = :currentCash WHERE id = :Id", Id = session["user_id"], currentCash = currentCash)
        stockRows = db.execute("SELECT count(*) FROM stocks WHERE user_id = :Id AND symbol=:symbol", Id = session["user_id"], symbol=symbol)
        if stockRows[0]["count(*)"] < 1 or stockRows==None:
            db.execute("INSERT INTO stocks (user_id, symbol, shares) VALUES(:Id, :symbol, :shares)", Id = session["user_id"], symbol=symbol.upper(), shares=shareMultiple)
            return redirect("/")
        else:
            curShares=db.execute("SELECT shares FROM stocks WHERE user_id=:Id AND symbol=:symbol", Id=session["user_id"], symbol=symbol)
            stockShares=curShares[0]["shares"]
            totalShares=stockShares+shareMultiple
            db.execute("UPDATE stocks SET shares=:totalShares WHERE user_id=:Id AND symbol=:symbol", totalShares=totalShares, Id=session["user_id"], symbol=symbol)
            return redirect("/")
    else:
        return render_template("buySearch.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please input a symbol")
        symbol = request.form.get("symbol")
        if lookup(symbol) == None:
            return apology("Please provide a correct symbol")
        quote = lookup(symbol)
        name = quote["name"]
        symbol = quote["symbol"]
        price = quote["price"] 
        price = usd(price)
        return render_template("quoted.html", symbol=symbol, price=price, name=name)
    else:
        return render_template("quote.html")
        


@app.route("/register", methods=["GET", "POST"])
def register():    
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

        # Ensure password was submitted that is the same
        elif not request.form.get("password1") or not request.form.get("confirmation") or request.form.get("password1") != request.form.get("confirmation"):
            return apology("Must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("Username"))

        # Checks to see if the username is taken
        if len(rows) != 0:
            return apology("Username already exists", 403)
        
        username = request.form.get("username")
        password = request.form.get("password1")
        hashpass = generate_password_hash(password)
        
        db.execute("INSERT INTO users (username, hash) VALUES(:name, :hashpass)", name=username, hashpass=hashpass)
        
        # Redirect user to home page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
    

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol=request.form.get("symbol")
        shares=db.execute("SELECT shares FROM stocks WHERE symbol=:symbol and user_id=:Id", symbol=symbol, Id=session["user_id"])
        subtract=float(request.form.get("shares"))
        user_total=db.execute("SELECT cash FROM users WHERE id=:Id", Id=session["user_id"])
        diction=lookup(symbol)
        add = subtract * diction["price"]
        new_total = user_total[0]["cash"] + add
        new = shares[0]["shares"] - subtract
        if(new < 0):
            return apology("Invalid shares")
        else:
            db.execute("UPDATE stocks SET shares=:new WHERE user_id=:Id AND symbol=:symbol", new=new, Id=session["user_id"], symbol=symbol)
            db.execute("UPDATE users SET cash=:new_total WHERE id=:Id", new_total=new_total, Id=session["user_id"])
            return redirect("/")
    else:
        zero=0
        symbolrows = db.execute("SELECT symbol FROM stocks WHERE user_id=:Id and shares != :zero", Id=session["user_id"], zero=zero)
        end = len(symbolrows)
        return render_template("sell.html", symbolrows=symbolrows, end=end)

@app.route("/cash", methods=["GET", "POST"])
@login_required
def cash():
    if request.method == "POST":
        money = int(request.form.get("money"))
        row = db.execute("SELECT cash FROM users WHERE id = :Id", Id = session["user_id"])
        bank = int(row[0]["cash"]) + money
        db.execute("UPDATE users SET cash = :bank WHERE id = :Id", Id = session["user_id"], bank = bank)
        return redirect("/")
    else:
        return render_template("cash.html")
    


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
