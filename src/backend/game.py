from typing import List, Dict, Optional
from src.backend.player import Player
import random
from src.backend.board import *

active_games = {}  # единое хранилище

class Game:
    def __init__(self, game_id: int, creator_id: int):
        self.game_id = game_id
        self.creator_id = creator_id
        self.players: List[Player] = []
        self.current_player_index = 0
        self.game_state = "waiting"  # waiting, playing, finished

    def add_player(self, player: Player):
        if self.game_state != "waiting":
            return False

        # уже есть такой юзер
        for p in self.players:
            if p.user_id == player.user_id:
                return False

        self.players.append(player)
        return True

    def start_game(self):
        if len(self.players) >= 2 and self.game_state == "waiting":
            self.game_state = "playing"
            return True
        return False

    @property
    def current_player(self) -> Optional[Player]:
        if self.players:
            return self.players[self.current_player_index]
        return None

    def roll_dice(self):
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        return d1, d2

    def next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def move_player(self, player: Player, steps: int):
        player.position = (player.position + steps) % 40  # 40 клеток стандартного поля

    def play_turn(self):
        if self.game_state != "playing":
            return "⏳ Игра ещё не начата!"

        player = self.current_player
        d1, d2 = self.roll_dice()
        total = d1 + d2
        self.move_player(player, total)

        msg = (
            f"🎲 {player.username} бросил кубики: {d1} + {d2} = {total}\n"
            f"🚶‍♂ Игрок переместился на клетку №{player.position}"
        )

        self.next_turn()
        return msg

    def init_board(self):
        self.board = [
            Go(),
            Street("Mediterranean Avenue", "brown", 60, [2, 10, 30, 90, 160, 250]),
            CommunityChest(),
            Street("Baltic Avenue", "brown", 60, [4, 20, 60, 180, 320, 450]),
            Tax("Income Tax", 200),
            Railroad("Reading Railroad", 200),
            Street("Oriental Avenue", "light_blue", 100, [6, 30, 90, 270, 400, 550]),
            Chance(),
            Street("Vermont Avenue", "light_blue", 100, [6, 30, 90, 270, 400, 550]),
            Street("Connecticut Avenue", "light_blue", 120, [8, 40, 100, 300, 450, 600]),
            Jail(),
            Street("St. Charles Place", "purple", 140, [10, 50, 150, 450, 625, 750]),
            Utility("Electric Company", 150),
            Street("States Avenue", "purple", 140, [10, 50, 150, 450, 625, 750]),
            Street("Virginia Avenue", "purple", 160, [12, 60, 180, 500, 700, 900]),
            Railroad("Pennsylvania Railroad", 200),
            Street("St. James Place", "orange", 180, [14, 70, 200, 550, 750, 950]),
            CommunityChest(),
            Street("Tennessee Avenue", "orange", 180, [14, 70, 200, 550, 750, 950]),
            Street("New York Avenue", "orange", 200, [16, 80, 220, 600, 800, 1000]),
            FreeParking(),
            GoToJail(),
        ]

    import random

    def roll_dice(self):
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        return d1, d2

    def move_current_player(self):
        player = self.current_player
        d1, d2 = self.roll_dice()
        steps = d1 + d2

        old_pos = player.position
        player.position = (player.position + steps) % len(self.board)

        # если прошёл через Go
        if player.position < old_pos:
            player.balance += 200

        cell = self.board[player.position]
        return d1, d2, cell


