class Player:
    def __init__(self, user_id: int, username: str, balance: int = 1500):
        self.user_id = user_id
        self.username = username
        self.balance = balance
        self.position = 0
        self.properties = []
        self.get_out_of_jail_free = False
        self.in_jail = False
        self.jail_turns = 0

    def __repr__(self):
        return f"Player({self.username}, ${self.balance})"
