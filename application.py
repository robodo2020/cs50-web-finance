import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from datetime import datetime
import psycopg2

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

# Configure CS50 Library to use database
db = SQL(os.getenv("DATABASE_URL"))
# db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    """Show portfolio of stocks"""


    stock_table = db.execute("SELECT symbol, name, shares FROM holdings WHERE uid =?", session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
    cash = float('%.2f' % cash[0]['cash'])
    cash_Total = cash
    CurrentStockPrice =[]
    print(stock_table)
    # deal with real time price
    for i in stock_table:
        CurrentStockPrice = lookup(i['symbol'])['price']
        i['price'] = CurrentStockPrice
        i['TOTAL'] = float('%.2f' % (CurrentStockPrice * i['shares']))
        cash_Total +=  i['TOTAL']
    # add all price to total


    return render_template("index.html", stock_table = stock_table, cash_Total  = float('%.2f' % cash_Total), cash = cash)

# Change Password

@app.route("/changepw", methods = ["GET","POST"])
@login_required
def changepw():
    if request.method =="GET":
        return render_template("changepw.html")
    else:
        originalpw = request.form.get("originalpw")
        newpw = request.form.get("newpw")
        newpwagain = request.form.get("newpwagain")

        # check original password match
        CheckOrgPw = db.execute("SELECT hash FROM users WHERE id =?", session["user_id"])
        if not check_password_hash(CheckOrgPw[0]["hash"], originalpw):
            return apology("Wrong Original Password", 403)

        if newpw == newpwagain:
            hashpassword = generate_password_hash(newpw)
            sql = "UPDATE users SET hash =? WHERE id =?"
            # val = (hashpassword ,session["user_id"])
            db.execute(sql, hashpassword ,session["user_id"])
            return redirect("/")
        else:
            return apology("New Passwords don't match", 400)
        return redirect("/")



# Account
@app.route("/account")
@login_required
def account():
        return render_template("account.html")

# deposit

@app.route("/deposit", methods = ["GET","POST"])
@login_required
def deposit():
    if request.method =="GET":
        return render_template("deposit.html")
    else:
        deposit_money = request.form.get("deposit_money")
        db.execute("UPDATE users SET cash = cash + ?", deposit_money)
    return redirect("/")



# Buy

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method =="GET":
        return render_template("buy.html")
    else:
        stock = request.form.get("stock")
        shares = int(request.form.get("shares"))
        stockresult = lookup(stock)

        # check if find the stock
        if stockresult == None:
            return apology("Symbol name error", 403)
        else:
            # calculate how much money user spend on that stock, and resultcash gets the how much cash they remains
            price = float('%.2f' % stockresult['price']) * shares
            cash = db.execute("SELECT cash FROM users WHERE id = ? ",session["user_id"])
            cash = cash[0]['cash']
            if price > cash:
                return apology("You do not have enough money", 403)
            else:
                resultcash = cash - price
                db.execute("UPDATE users SET cash = ? WHERE id = ?", resultcash, session["user_id"])

            # add stock info user buy into table
            # check if the user already has the stock in holdings table
            UserStock = db.execute("SELECT * FROM holdings WHERE symbol = ? AND UID = ?", stock, session["user_id"])
            if UserStock == []:
                sql = "INSERT INTO holdings VALUES(?, ?, ?, ?)"
                # val = (stockresult['symbol'], stockresult['name'], str(shares), session["user_id"])
                db.execute(sql,stockresult['symbol'], stockresult['name'], str(shares), session["user_id"])
            else:
                totshares = UserStock[0]['shares'] + shares
                db.execute("UPDATE holdings SET Shares = ? WHERE symbol = ? AND uid = ?", totshares, stock, session["user_id"])
            now = datetime.now()
            date_time = now.strftime("%Y/%m/%d %H:%M:%S")

            # update transaction history table
            db.execute("INSERT INTO history VALUES(?, ?, ?, ?, ?)", stockresult['symbol'], shares, stockresult['price'], date_time, session["user_id"])
            return redirect("/")




# History


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history_table = db.execute("SELECT * FROM history WHERE UID = %s", session["user_id"])

    return render_template("history.html", history_table = history_table)




# Login

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST
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


# Log out

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



# Quote

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        stock = request.form.get("stock")
        stockresult = lookup(stock)
        # check if find the stock
        if stockresult == None:
            return apology("Symbol name error", 400)
        else:

            return render_template("quoted.html", name = stockresult['name'], price = stockresult['price'], symbol = stockresult['symbol'] )


# Register

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("name")
        password = request.form.get("password")
        passwordagain = request.form.get("passwordagain")
        if password == passwordagain:
            hashpassword = generate_password_hash(password)
            sql = "INSERT INTO users (username, hash) VALUES (?, ?)"
            db.execute(sql, username ,hashpassword)
            return redirect("/login")
        else:
            return apology("Passwords don't match", 400)



# Sell

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    OwnStock = db.execute("SELECT symbol, shares from holdings WHERE uid = ?", session["user_id"])
    if request.method == "GET":
        return render_template("sell.html", OwnStock = OwnStock)
    else:
        SellStock = request.form.get("SellStock")
        SellSharesNum = int(request.form.get("SellSharesNum"))
        StockToSell = db.execute("SELECT * FROM holdings WHERE symbol = ? AND uid=?", SellStock, session["user_id"])

        if SellSharesNum > int(StockToSell[0]['shares']):
            return apology("Shares insufficient", 400)

        # update holding table
        db.execute("UPDATE holdings SET shares = shares - ? WHERE symbol = ? AND uid = ?", SellSharesNum, SellStock, session["user_id"])

        # calculate current cash
        SellPrice = lookup(SellStock)['price'] * SellSharesNum
        now = datetime.now()
        date_time = now.strftime("%Y/%m/%d %H:%M:%S")

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", SellPrice, session["user_id"])
        # db.execute("INSERT INTO history VALUES(?, ?, ?, ?, ?)", stockresult['symbol'], shares, stockresult['price'], date_time, session["user_id"])
        db.execute("INSERT INTO history VALUES(?, ?, ?, ?, ?)", SellStock, -SellSharesNum, lookup(SellStock)['price'], date_time, session["user_id"])
    return redirect("/")





def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)