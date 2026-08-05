import unittest
from app.scoring import determine_server, compute_scores_and_games
from app.models import Event

class TestCSVExportLogic(unittest.TestCase):
    def test_determine_server_rotation_for_csv(self):
        # Game 1: 0-0 -> Player 1 serves
        self.assertEqual(determine_server(0, 0, 1, "player1"), "player1")
        # Game 1: 2-0 -> Player 2 serves
        self.assertEqual(determine_server(2, 0, 1, "player1"), "player2")
        # Game 1: 10-10 -> Deuce, alternates every 1 point
        self.assertEqual(determine_server(10, 10, 1, "player1"), "player1")
        self.assertEqual(determine_server(10, 11, 1, "player1"), "player2")
        # Game 2: Player 2 serves first in Game 2
        self.assertEqual(determine_server(0, 0, 2, "player1"), "player2")

if __name__ == "__main__":
    unittest.main()
