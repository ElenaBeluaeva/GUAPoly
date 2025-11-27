# src/backend/board.py

class Cell:
    def __init__(self, name: str):
        self.name = name

    def on_land(self, player, game):
        pass


class Go(Cell):
    def __init__(self):
        super().__init__("Go")


class Street(Cell):
    def __init__(self, name, color, price, rent_levels):
        super().__init__(name)
        self.color = color
        self.price = price
        self.rent_levels = rent_levels
        self.owner = None
        self.houses = 0


class Railroad(Cell):
    def __init__(self, name, price):
        super().__init__(name)
        self.price = price
        self.owner = None


class Utility(Cell):
    def __init__(self, name, price):
        super().__init__(name)
        self.price = price
        self.owner = None


class Tax(Cell):
    def __init__(self, name, amount):
        super().__init__(name)
        self.amount = amount


class Chance(Cell):
    def __init__(self):
        super().__init__("Chance")


class CommunityChest(Cell):
    def __init__(self):
        super().__init__("Community Chest")


class Jail(Cell):
    def __init__(self):
        super().__init__("Jail")


class GoToJail(Cell):
    def __init__(self):
        super().__init__("Go To Jail")


class FreeParking(Cell):
    def __init__(self):
        super().__init__("Free Parking")
