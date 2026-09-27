import unittest
from app.models import Event
from app.scoring import compute_match_analytics, determine_server, compute_scores_and_games

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
        """Verify full match analytics calculation including serve win %, duration buckets (0-6s, 6-10s, 10s+), serve ratio, and self-serve win rate."""
        p1 = "Alice"
        p2 = "Bob"
        
        events = [
            # Point 1: 0-0, Server Alice, Winner Alice (Short 3.0s, Alice self-serve win)
            Event(start=10.0, end=13.0, winner=p1, game=1),
            # Point 2: 1-0, Server Alice, Winner Bob (Short 5.0s, Alice self-serve loss)
            Event(start=20.0, end=25.0, winner=p2, game=1),
            # Point 3: 1-1, Server Bob, Winner Bob (Medium 8.0s, Bob self-serve win)
            Event(start=30.0, end=38.0, winner=p2, game=1),
            # Point 4: 1-2, Server Bob, Winner Alice (Medium 10.0s, Bob self-serve loss)
            Event(start=50.0, end=60.0, winner=p1, game=1),
            # Point 5: 2-2, Server Alice, Winner Alice (Long 12.0s, Alice self-serve win)
            Event(start=70.0, end=82.0, winner=p1, game=1),
        ]

        stats = compute_match_analytics(events, player1=p1, player2=p2, first_server="player1")

        # Check Overall Serve Win %:
        # Alice served 3 points (0-0, 1-0, 2-2), won 2 -> 66.7%
        # Bob served 2 points (1-1, 1-2), won 1 -> 50.0%
        self.assertEqual(stats["serve_stats"][p1]["served_total"], 3)
        self.assertEqual(stats["serve_stats"][p1]["served_won"], 2)
        self.assertEqual(stats["serve_stats"][p1]["serve_win_pct"], 66.7)

        self.assertEqual(stats["serve_stats"][p2]["served_total"], 2)
        self.assertEqual(stats["serve_stats"][p2]["served_won"], 1)
        self.assertEqual(stats["serve_stats"][p2]["serve_win_pct"], 50.0)

        # Check Rally Duration Buckets:
        # Short (0-6s): 2 rallies (Point 1: 3s won by P1, Point 2: 5s won by P2)
        self.assertEqual(stats["duration_stats"]["short"]["total"], 2)
        self.assertEqual(stats["duration_stats"]["short"]["p1_won"], 1)
        self.assertEqual(stats["duration_stats"]["short"]["p2_won"], 1)
        self.assertEqual(stats["duration_stats"]["short"]["p1_win_pct"], 50.0)
        self.assertEqual(stats["duration_stats"]["short"]["p2_win_pct"], 50.0)
        self.assertEqual(stats["duration_stats"]["short"]["p1_served"], 2)
        self.assertEqual(stats["duration_stats"]["short"]["p2_served"], 0)
        self.assertEqual(stats["duration_stats"]["short"]["p1_serve_pct"], 100.0)
        self.assertEqual(stats["duration_stats"]["short"]["p2_serve_pct"], 0.0)
        self.assertEqual(stats["duration_stats"]["short"]["p1_self_serve_won"], 1)
        self.assertEqual(stats["duration_stats"]["short"]["p1_self_serve_win_pct"], 50.0)
        self.assertEqual(stats["duration_stats"]["short"]["p2_self_serve_won"], 0)
        self.assertEqual(stats["duration_stats"]["short"]["p2_self_serve_win_pct"], 0.0)

        # Medium (6-10s): 2 rallies (Point 3: 8s won by P2, Point 4: 10s won by P1)
        self.assertEqual(stats["duration_stats"]["medium"]["total"], 2)
        self.assertEqual(stats["duration_stats"]["medium"]["p1_won"], 1)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_won"], 1)
        self.assertEqual(stats["duration_stats"]["medium"]["p1_win_pct"], 50.0)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_win_pct"], 50.0)
        self.assertEqual(stats["duration_stats"]["medium"]["p1_served"], 0)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_served"], 2)
        self.assertEqual(stats["duration_stats"]["medium"]["p1_serve_pct"], 0.0)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_serve_pct"], 100.0)
        self.assertEqual(stats["duration_stats"]["medium"]["p1_self_serve_won"], 0)
        self.assertEqual(stats["duration_stats"]["medium"]["p1_self_serve_win_pct"], 0.0)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_self_serve_won"], 1)
        self.assertEqual(stats["duration_stats"]["medium"]["p2_self_serve_win_pct"], 50.0)

        # Long (10s+): 1 rally (Point 5: 12s won by P1)
        self.assertEqual(stats["duration_stats"]["long"]["total"], 1)
        self.assertEqual(stats["duration_stats"]["long"]["p1_won"], 1)
        self.assertEqual(stats["duration_stats"]["long"]["p2_won"], 0)
        self.assertEqual(stats["duration_stats"]["long"]["p1_win_pct"], 100.0)
        self.assertEqual(stats["duration_stats"]["long"]["p2_win_pct"], 0.0)
        self.assertEqual(stats["duration_stats"]["long"]["p1_served"], 1)
        self.assertEqual(stats["duration_stats"]["long"]["p2_served"], 0)
        self.assertEqual(stats["duration_stats"]["long"]["p1_serve_pct"], 100.0)
        self.assertEqual(stats["duration_stats"]["long"]["p2_serve_pct"], 0.0)
        self.assertEqual(stats["duration_stats"]["long"]["p1_self_serve_won"], 1)
        self.assertEqual(stats["duration_stats"]["long"]["p1_self_serve_win_pct"], 100.0)
        self.assertEqual(stats["duration_stats"]["long"]["p2_self_serve_won"], 0)
        self.assertEqual(stats["duration_stats"]["long"]["p2_self_serve_win_pct"], 0.0)

        # Check Streaks & Pace:
        self.assertEqual(stats["momentum"]["max_streak"][p1], 2) # Points 4 & 5
        self.assertEqual(stats["momentum"]["max_streak"][p2], 2) # Points 2 & 3
        self.assertEqual(stats["momentum"]["avg_duration_sec"], 7.6) # (3+5+8+10+12)/5 = 38/5 = 7.6
        self.assertEqual(stats["momentum"]["longest_rally_sec"], 12.0)

    def test_scoring_logic_score_after(self):
        """
        Verify that compute_scores_and_games properly derives score after points,
        and advances game counts when reaching 11 points (win by 2).
        """
        p1 = "Jonsen"
        p2 = "Ryan"
        events = [
            Event(start=1.0, end=3.0, winner="Jonsen"),
            Event(start=4.0, end=6.0, winner="Ryan"),
            Event(start=7.0, end=9.0, winner="Jonsen"),
        ]
        scored = compute_scores_and_games(events, p1, p2)
        self.assertEqual(len(scored), 3)
        self.assertEqual(scored[0].game, 1)
        self.assertEqual(scored[1].game, 1)
        self.assertEqual(scored[2].game, 1)

if __name__ == "__main__":
    unittest.main()
