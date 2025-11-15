from typing import List, Dict, Optional
from .player import Player


class Game:
    def __init__(self, game_id: int, creator_id: int):
        self.game_id = game_id
        self.creator_id = creator_id
        self.players: List[Player] = []
        self.current_player_index = 0
        self.game_state = "waiting"  # waiting, playing, finished
        self.active_games: Dict[int, 'Game'] = {}

    def add_player(self, player: Player):
        if self.game_state == "waiting":
            self.players.append(player)
            return True
        return False

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
