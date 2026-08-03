import unittest
from app.models import Event
from app.scoring import compute_match_analytics, determine_server

class TestScoringAnalytics(unittest.TestCase):
    """Test suite for Table Tennis Match Analytics calculations."""

    def test_determine_server_normal_rotation(self):
        """Verify ITTF 2-point service rotation logic in normal play (<10-10)."""
        # Game 1, P1 served first
        self.assertEqual(determine_server(p1_score=0, p2_score=0, game_num=1, first_server_game1="player1"), "player1")
        self.assertEqual(determine_server(p1_score=1, p2_score=0, game_num=1, first_server_game1="player1"), "player1")
        self.assertEqual(determine_server(p1_score=1, p2_score=1, game_num=1, first_server_game1="player1"), "player2")
        self.assertEqual(determine_server(p1_score=2, p2_score=1, game_num=1, first_server_game1="player1"), "player2")
        self.assertEqual(determine_server(p1_score=2, p2_score=2, game_num=1, first_server_game1="player1"), "player1")

    def test_determine_server_game_transition(self):
        """Verify service swap between games (P1 served first in Game 1 -> P2 serves first in Game 2)."""
        # Game 2, P1 served first in Game 1 -> P2 serves first in Game 2
        self.assertEqual(determine_server(p1_score=0, p2_score=0, game_num=2, first_server_game1="player1"), "player2")
        self.assertEqual(determine_server(p1_score=1, p2_score=0, game_num=2, first_server_game1="player1"), "player2")
        self.assertEqual(determine_server(p1_score=1, p2_score=1, game_num=2, first_server_game1="player1"), "player1")

    def test_determine_server_deuce_rule(self):
        """Verify deuce service rotation (alternate every 1 point at 10-10 or higher)."""
        # 10-10 (20 total points) -> Game 1, P1 first server -> P1
        self.assertEqual(determine_server(p1_score=10, p2_score=10, game_num=1, first_server_game1="player1"), "player1")
        # 10-11 (21 total points) -> alternate to P2
        self.assertEqual(determine_server(p1_score=10, p2_score=11, game_num=1, first_server_game1="player1"), "player2")
        # 11-11 (22 total points) -> alternate to P1
        self.assertEqual(determine_server(p1_score=11, p2_score=11, game_num=1, first_server_game1="player1"), "player1")

    def test_compute_match_analytics_serve_and_duration_stats(self):
        """Verify full match analytics calculation including serve win % and duration buckets."""
        p1 = "Alice"
        p2 = "Bob"
        
        events = [
            # Point 1: 0-0, Server Alice, Winner Alice (Short 3.0s)
            Event(start=10.0, end=13.0, winner=p1, game=1, score_before="0-0"),
            # Point 2: 1-0, Server Alice, Winner Bob (Medium 5.0s)
            Event(start=20.0, end=25.0, winner=p2, game=1, score_before="1-0"),
            # Point 3: 1-1, Server Bob, Winner Alice (Long 10.0s)
            Event(start=30.0, end=40.0, winner=p1, game=1, score_before="1-1"),
            # Point 4: 2-1, Server Bob, Winner Alice (Short 2.0s)
            Event(start=50.0, end=52.0, winner=p1, game=1, score_before="2-1"),
        ]

        stats = compute_match_analytics(events, player1=p1, player2=p2, first_server="player1")

        # Check Serve Win %:
        # Alice served 2 points (0-0, 1-0), won 1 -> 50.0%
        # Bob served 2 points (1-1, 2-1), won 0 -> 0.0%
        self.assertEqual(stats["serve_stats"][p1]["served_total"], 2)
        self.assertEqual(stats["serve_stats"][p1]["served_won"], 1)
        self.assertEqual(stats["serve_stats"][p1]["serve_win_pct"], 50.0)

        self.assertEqual(stats["serve_stats"][p2]["served_total"], 2)
        self.assertEqual(stats["serve_stats"][p2]["served_won"], 0)
        self.assertEqual(stats["serve_stats"][p2]["serve_win_pct"], 0.0)

        # Check Rally Duration Buckets:
        # Short (<4s): 2 rallies (Point 1: 3s won by P1, Point 4: 2s won by P1)
        self.assertEqual(stats["duration_stats"]["short"]["total"], 2)
        self.assertEqual(stats["duration_stats"]["short"]["p1_won"], 2)
        self.assertEqual(stats["duration_stats"]["short"]["p1_win_pct"], 100.0)

        # Medium (4-8s): 1 rally (Point 2: 5s won by P2)
        self.assertEqual(stats["duration_stats"]["medium"]["total"], 1)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_won"], 1)

        # Long (>8s): 1 rally (Point 3: 10s won by P1)
        self.assertEqual(stats["duration_stats"]["long"]["total"], 1)
        self.assertEqual(stats["duration_stats"]["long"]["p1_won"], 1)

        # Check Streaks & Pace:
        self.assertEqual(stats["momentum"]["max_streak"][p1], 2) # Points 3 & 4 in a row
        self.assertEqual(stats["momentum"]["max_streak"][p2], 1)
        self.assertEqual(stats["momentum"]["avg_duration_sec"], 5.0)
        self.assertEqual(stats["momentum"]["longest_rally_sec"], 10.0)

if __name__ == "__main__":
    unittest.main()
