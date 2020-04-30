import os
import datetime
from storage import Storage

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, lookup, usd, login_required2


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


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

storage = Storage(db)



@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    positions = storage.get_positions(user_id)
    grand_total = 0
    for position in positions:
        stock = lookup(position["symbol"])
        total = position["quantity"] * stock["price"]
        grand_total += total
        position["company"] = stock["name"]
        position["price"] = stock["price"]
        position["total"] = usd(total)

    user_cash = storage.get_cash(session["user_id"])
    grand_total += user_cash

    return render_template("index.html",
                        positions=positions,
                        cash=usd(user_cash),
                        grand_total=usd(grand_total))

class HTTPException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code


class ApiException(Exception):
    def __init__(self, message, code = 400):
        self.message = message
        self.code = code


@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, ApiException):
        return jsonify(message=error.message), error.code
    if isinstance(error, HTTPException):
        return apology(error.message, error.code)
    raise error
    # return apology("Really Bad Thing Happened")


@app.route("/api/user", methods=["GET"])
@login_required2
def api_user():
    user = storage.get_user_by_id(session["user_id"])

    if user is None:
        return "", 401
    else:
        return jsonify({"user": user})


@app.route("/api/buy", methods=["POST"])
@login_required
def api_buy2():
    symbol = request.form.get("symbol")
    shares = request.form.get("shares")

    if symbol is "":
        raise ApiException("symbol can't be empty", 403)

    if shares is "":
        raise ApiException("must provide shares", 403)

    quantity = int(shares)
    if quantity < 1:
        raise ApiException("number of shares must be 1 or greater", 403)

    stock = lookup(symbol)
    if stock is None:
        raise ApiException("invalid stock symbol", 403)

    cash = storage.get_cash(session["user_id"])
    stocks_cost = stock["price"] * quantity
    if not cash >= stocks_cost:
        raise ApiException("not enough cash")

    insert_transaction(stock, quantity)
    left = cash - stocks_cost
    storage.update_cash(session["user_id"], left)
    position_update(stock, quantity)

    return "", 200


@app.route("/buy2", methods=["GET"])
@login_required
def buy2():
    return render_template("buy2.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")

        if symbol is None:
            raise HTTPException("must provide correct symbol", 403)

        if shares is None:
            raise HTTPException("must provide shares", 403)

        quantity = int(shares)

        if quantity < 1:
            raise HTTPException("number of shares must be 1 or greater", 403)
        cash = storage.get_cash(session["user_id"])
        stocks_cost = symbol["price"] * quantity
        if cash >= stocks_cost:
            insert_transaction(symbol, quantity)
            left = cash - stocks_cost
            storage.update_cash(session["user_id"], left)
            position_update(symbol, quantity)
        else:
            raise HTTPException("not enough cash")

        return redirect("/")

    else:
        return render_template("buy.html")


def insert_transaction(symbol, shares):
    stocks_cost = symbol["price"] * int(shares)
    company = symbol["name"]
    quantity=shares
    price = symbol["price"]
    date = datetime.datetime.now()
    user_id = session["user_id"]
    stock_symbol = symbol["symbol"]

    storage.add_transaction(user_id, company, quantity, price, date, stock_symbol)

def position_update(symbol, quantity):
    existing_position = storage.get_position(session["user_id"], symbol["symbol"])
    if existing_position is not None:
        new_quantity = existing_position["quantity"] + quantity
        storage.update_position_quantity(session["user_id"], symbol["symbol"], new_quantity)
    else:
        storage.add_position(session["user_id"], symbol["symbol"], quantity)



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = storage.get_transactions(user_id)
    for transaction in transactions:
        symbol = transaction["symbol"]
        shares = transaction["quantity"]
        price = transaction["price"]
        date = transaction["date"]

    return render_template("history.html",
                        transactions=transactions)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            raise HTTPException("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            raise HTTPException("must provide password", 403)

        # Query database for username
        username = request.form.get("username")
        user = storage.get_user_by_username(username)

        # Ensure username exists and password is correct
        if user is None or not check_password_hash(user["hash"], request.form.get("password")):
            raise HTTPException("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user["id"]

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
    # session.clear()
    if request.method == "POST":
        symbol = request.form.get("symbol")
        result = lookup(symbol)
        return render_template("quoted.html", result=result)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conf_passw = request.form.get("confirmation")
        if not username:
            raise HTTPException("must provide username", 403)
        elif not password:
            raise HTTPException("must provide password", 403)
        elif not conf_passw:
            raise HTTPException("must provide password confirmation", 403)

        if password != conf_passw:
            raise HTTPException("different passwords, must be the same", 403)
        else:
            hash_pass = generate_password_hash(password)
            user = storage.get_user_by_username(username)

            if user is None:
                storage.add_new_user(username, hash_pass)
                return redirect("/")
            else:
                raise HTTPException("this username is already created", 400)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")

        if symbol is None:
            raise HTTPException("must provide correct symbol", 403)

        if shares is None:
            raise HTTPException("must provide shares", 403)

        selling_quantity = int(shares)
        existing_quantity = storage.get_position(session["user_id"], symbol["symbol"])
        existing_quantity = int(existing_quantity["quantity"])


        if selling_quantity > existing_quantity:
            raise HTTPException("you don't have enough shares", 403)
        else:
            date = datetime.datetime.now()
            storage.add_transaction(session["user_id"], symbol["name"], selling_quantity * -1, symbol["price"], date, symbol["symbol"] )

            existing_cash = storage.get_cash(session["user_id"])
            cash = selling_quantity * symbol["price"] + existing_cash
            storage.update_cash(session["user_id"], cash)

            if selling_quantity < existing_quantity:
                new_quantity = existing_quantity - selling_quantity
                storage.update_position_quantity(session["user_id"], symbol["symbol"], new_quantity)
            elif selling_quantity == existing_quantity:
                storage.delete_position(session["user_id"], symbol["symbol"])
            return redirect("/")
    else:
        user_id = session["user_id"]
        symbols = storage.get_user_stocks(user_id)
        return render_template("sell.html", symbols=symbols)



if __name__ == '__main__':
    app.run()