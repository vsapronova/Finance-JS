class Storage:
    def __init__(self, db):
        self.db = db

    def get_user_by_username(self, username):
        users = self.db.execute("SELECT * FROM users WHERE username = :username", username=username)
        if len(users) < 1:
            return None
        return users[0]

    def get_user_by_id(self, user_id, with_hash = False):
        users = self.db.execute("SELECT * FROM users WHERE id = :user_id", user_id=user_id)
        if len(users) < 1:
            return None
        user =users[0]
        if not with_hash:
            user.pop("hash", None)
        return user

    def get_user_stocks(self, user_id):
        return self.db.execute("SELECT DISTINCT symbol FROM positions WHERE user_id=:user_id", user_id=user_id)

    def add_new_user(self, username, hash_pass):
        return self.db.execute(f"INSERT INTO users (username, hash, cash) VALUES ('{username}', '{hash_pass}', '10000')")


    def get_positions(self, user_id):
        return self.db.execute("SELECT * FROM positions WHERE user_id=:user_id", user_id=user_id)

    def get_position(self, user_id, symbol):
        position = self.db.execute("SELECT * FROM positions WHERE user_id = :id AND symbol = :symbol", id=user_id, symbol=symbol)
        if len(position) < 1:
            return None
        return position[0]

    def add_position(self, user_id, symbol, quantity):
        self.db.execute("INSERT INTO positions(user_id, symbol, quantity) VALUES (:user_id, :symbol, :quantity)",
        user_id=user_id,
        symbol=symbol,
        quantity=quantity)

    def update_position_quantity(self, user_id, symbol, quantity):
        self.db.execute("UPDATE positions SET quantity = :quantity WHERE symbol = :symbol AND user_id = :user_id",
        quantity=quantity,
        symbol=symbol,
        user_id=user_id)

    def get_transactions(self, user_id):
        return self.db.execute("SELECT * FROM transactions WHERE user_id = :user_id", user_id=user_id)

    def add_transaction(self, user_id, company, quantity, price, date, symbol):
        self.db.execute("INSERT INTO transactions(user_id, company, quantity, price, date, symbol) VALUES (:user_id, :company, :quantity, :price, :date, :symbol)",
        user_id=user_id,
        company=company,
        quantity=quantity,
        price=price,
        date=date,
        symbol=symbol)

    def get_cash(self, user_id):
        result = self.db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=user_id)
        return result[0]["cash"]

    def update_cash(self, user_id, cash):
        self.db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=cash, user_id=user_id )

    def delete_position(self, user_id, symbol):
        self.db.execute("DELETE FROM positions WHERE user_id = :user_id AND symbol = :symbol AND quantity = 0",
        user_id=user_id,
        symbol=symbol)
