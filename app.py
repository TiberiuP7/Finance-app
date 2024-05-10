import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id= session["user_id"]

    user=db.execute("SELECT username FROM users WHERE id= ?", id)
    for x in user:
        name= x
        break
    noun=name["username"]
    stocks= db.execute("SELECT * FROM portofolio WHERE user= ? AND shares <> 0 AND type <> 'SELL'", noun)
    total2=0

    # Update table with price and name of each stock

    for stock in stocks:
        x= lookup(stock["symbol"])
        shares= stock["shares"]
        

        total= shares

        total2= total2 + total
        db.execute("UPDATE portofolio SET value= ? WHERE symbol= ? AND user= ?", total, stock["symbol"], noun)

    cash=db.execute("SELECT cash FROM users WHERE id= ?", id)
    for x in cash:
        dime= x
        break
    money= dime["cash"]
    db.execute("UPDATE portofolio SET cash = ? WHERE user= ?", dime["cash"], noun)
    grand= total2 + int(dime["cash"])
    return render_template("index.html", stocks=stocks, cash=money, grand=grand)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        stock= lookup(request.form.get("symbol"))
        if not request.form.get("symbol") or stock == None:
            return apology("must provide existing symbol", 400)
        id = session["user_id"]

        # Check if input is a number
        shares= request.form.get("shares")
        try:
            sharez=int(shares)
        except ValueError:
            return apology("must provide a number", 400)

        if int(request.form.get("shares")) <= 0:
            return apology("must provide positive number of shares", 400)


        money= db.execute("SELECT cash FROM users WHERE id= ?", id)
        for x in money:
            cash = x
            break

        price= stock["price"]
        buy = sharez * price

        if buy > cash["cash"]:
            return apology("cannot afford purchase", 400)
        else:
            cash1= cash["cash"] - buy
            user=db.execute("SELECT username FROM users WHERE id = ?", id)
            for x in user:
                name= x
                break
            value= int(shares)* int(price)
            total= cash1 + value
            time= datetime.now()
            db.execute("INSERT INTO portofolio (time, type, user, shares, symbol, cash, price, value, total) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?)", time, 'BUY', name["username"], request.form.get("shares"), stock["symbol"], cash1, price, value, total )
            db.execute("UPDATE users SET cash= ? WHERE id= ?", cash1, id )
            return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id= session["user_id"]

    user=db.execute("SELECT username FROM users WHERE id= ?", id)
    for x in user:
        name= x
        break
    noun=name["username"]
    transactions= db.execute("SELECT time, type, symbol, shares, price FROM portofolio WHERE user= ?", noun)

    return render_template("history.html", transactions= transactions)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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
        quote= lookup(request.form.get("symbol"))
        if quote == None:
            return apology("provided symbol doesn't exist", 400)
        name= quote["name"]
        price= quote["price"]
        symbol=quote["symbol"]
        return render_template("quoted.html", name = name, price=price, symbol=symbol)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
                return apology("must provide username", 400)

        if not request.form.get("password"):
            return apology("must provide password", 400)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        user = db.execute("SELECT * FROM users WHERE username= ?", request.form.get("username"))
        if len(user) != 0:
            return apology("username already in use", 400)

        hash= generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), hash)

        rows = db.execute("SELECT id FROM users WHERE username= ?", request.form.get("username"))
        session["user_id"]= rows[0]["id"]
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("shares"):
            return apology("must provide a positive number of shares", 400)
        if not request.form.get("symbol"):
            return apology("must select a symbol to sell", 400)
        id=session["user_id"]
        user=db.execute("SELECT username FROM users WHERE id = ?", id)
        for x in user:
            name= x
            break
        stocks=db.execute("SELECT symbol FROM portofolio WHERE user= ?", name["username"])


        # Shares and symbol to sell
        sell= request.form.get("symbol")
        shares=request.form.get("shares")
        # Shares the user has
        existing= db.execute("SELECT shares FROM portofolio WHERE symbol= ? AND user= ?", sell, name["username"])
        for x in existing:
            exist= x
            break
        try:
            sharez=int(shares)
        except ValueError:
            return apology("must provide a numeric value", 408)

        if int(exist["shares"]) < sharez:
            return apology("not enough shares to sell", 408)
        else:
            # Update the portofolio
            diff= int(exist["shares"]) - int(shares)
            time=datetime.now()
            y=lookup(sell)
            price=y["price"]
            value= int(price) * int(shares)
            db.execute("UPDATE portofolio SET shares= ? WHERE symbol= ? AND user= ?", diff, sell, name["username"])
            db.execute("INSERT INTO portofolio (type, time, user, shares, price, symbol) VALUES(?, ?, ?, ?, ?, ?)", 'SELL', time, name["username"], shares, usd(price), sell)

            cash=db.execute("SELECT cash FROM users WHERE username= ?", name["username"])
            for x in cash:
                dime= x
                break


            money= int(dime["cash"]) + int(value)
            # Update new cash balance
            db.execute("UPDATE users SET cash= ? WHERE username= ?", money, name["username"])
        return redirect("/")
    else:
        id=session["user_id"]
        user=db.execute("SELECT username FROM users WHERE id= ?", id)
        for x in user:
            name= x
            break
        stocks=db.execute("SELECT DISTINCT symbol FROM portofolio WHERE user= ? AND shares<>0 AND type <> 'SELL'", name["username"])
        symbols=[]
        for stock in stocks:
            x= stock
            symbols.append(x["symbol"])
        return render_template("sell.html", symbols=symbols)

@app.route("/wallet", methods=["GET", "POST"])
@login_required
def wallet():
    if request.method == "POST":
        if not request.form.get("cash"):
            return apology("specify amount of cash", 400)
        if not request.form.get("type"):
            return apology("specify transaction type", 400)
        try:
            cash=int(request.form.get("cash"))
        except ValueError:
            return apology("must provide a numeric value", 400)
        id=session["user_id"]
        user=db.execute("SELECT username FROM users WHERE id = ?", id)
        for x in user:
            name= x
            break
        balance=db.execute("SELECT cash FROM users WHERE username= ?", name["username"])
        for x in balance:
            money= x
            break

        if request.form.get("type") == 'ADD':
            cash=cash+int(money["cash"])
            db.execute("UPDATE users SET cash= ? WHERE username= ?", cash, name["username"])
        else:
            cash= int(money["cash"]) - cash
            db.execute("UPDATE users SET cash= ? WHERE username= ?", cash, name["username"])
        return redirect("/")
    else:
        return render_template("wallet.html")



