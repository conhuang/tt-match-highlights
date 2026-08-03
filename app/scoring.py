from typing import List
from app.models import Event

def compute_scores_and_games(events: List[Event], player1: str, player2: str) -> List[Event]:
    """
    Sorts events chronologically and computes the correct 'score_before' 
    and 'game' number for each point, handling table tennis rules:
    - Game goes up to 11.
    - Must win by 2 points (deuce rules).
    - Game count increments and score resets to 0-0 once a game is won.
    """
    # Sort events by their start timestamp
    sorted_events = sorted(events, key=lambda e: e.start)
    
    p1_score = 0
    p2_score = 0
    current_game = 1
    
    for event in sorted_events:
        # 1. Assign the state BEFORE this point was played
        event.score_before = f"{p1_score}-{p2_score}"
        event.game = current_game
        
        # 2. Update scores based on the winner of this point
        if event.winner == player1:
            p1_score += 1
        elif event.winner == player2:
            p2_score += 1
        # If winner is None (e.g. it was just a clip segment log), scores do not change
        
        # 3. Check if the game was won by this point
        # A game is won by the first player to reach 11 points, unless it's deuce (10-10),
        # where they must win by a margin of 2 points.
        if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
            # Game complete! Reset scores and advance game count
            p1_score = 0
            p2_score = 0
            current_game += 1
            
    return sorted_events

def determine_server(p1_score: int, p2_score: int, game_num: int, first_server_game1: str = "player1") -> str:
    """
    Determines whether 'player1' or 'player2' is serving for a given score in a game
    according to official ITTF table tennis service rules:
    - Serves alternate every 2 points during normal play (< 10-10).
    - Serves alternate every 1 point during deuce play (>= 10-10).
    - The player who received first in Game N serves first in Game N+1.
    """
    # 1. Determine first server for current game
    if game_num % 2 != 0:
        first_in_game = first_server_game1
    else:
        first_in_game = "player2" if first_server_game1 == "player1" else "player1"

    opposite_in_game = "player2" if first_in_game == "player1" else "player1"

    # 2. Check for Deuce rule (10-10 or higher)
    if p1_score >= 10 and p2_score >= 10:
        total_pts = p1_score + p2_score
        turns = total_pts - 20
        return first_in_game if (turns % 2 == 0) else opposite_in_game
    else:
        total_pts = p1_score + p2_score
        turns = total_pts // 2
        return first_in_game if (turns % 2 == 0) else opposite_in_game


def compute_match_analytics(events: List[Event], player1: str, player2: str, first_server: str = "player1") -> dict:
    """
    Computes zero-extra-input Table Tennis match analytics:
    - Serve Win Ratio & Return Win Ratio for both players.
    - Win Rate grouped by Rally Duration (<4s short, 4-8s medium, >8s long).
    - Momentum & Streaks (Max consecutive points, average rally length, longest rally).
    """
    sorted_events = sorted(events, key=lambda e: e.start)

    # 1. Initialize stats structures
    serve_stats = {
        player1: {"served_total": 0, "served_won": 0, "serve_win_pct": 0.0, "return_won": 0},
        player2: {"served_total": 0, "served_won": 0, "serve_win_pct": 0.0, "return_won": 0}
    }

    duration_buckets = {
        "short": {"total": 0, "p1_won": 0, "p2_won": 0, "p1_win_pct": 0.0, "p2_win_pct": 0.0, "label": "< 4 sec (Serve & 3rd Ball)"},
        "medium": {"total": 0, "p1_won": 0, "p2_won": 0, "p1_win_pct": 0.0, "p2_win_pct": 0.0, "label": "4 - 8 sec (Standard Exchange)"},
        "long": {"total": 0, "p1_won": 0, "p2_won": 0, "p1_win_pct": 0.0, "p2_win_pct": 0.0, "label": "> 8 sec (Endurance & Deep Rally)"}
    }

    p1_current_streak = 0
    p1_max_streak = 0
    p2_current_streak = 0
    p2_max_streak = 0

    durations = []
    longest_rally_sec = 0.0
    longest_rally_start = 0.0

    for event in sorted_events:
        if not event.winner:
            continue

        # Parse score before point
        p1_score, p2_score = 0, 0
        if event.score_before and "-" in event.score_before:
            try:
                parts = event.score_before.split("-")
                p1_score = int(parts[0])
                p2_score = int(parts[1])
            except ValueError:
                pass

        # Determine server
        server_key = determine_server(p1_score, p2_score, event.game or 1, first_server)
        server_name = player1 if server_key == "player1" else player2
        receiver_name = player2 if server_key == "player1" else player1

        serve_stats[server_name]["served_total"] += 1
        if event.winner == server_name:
            serve_stats[server_name]["served_won"] += 1
        else:
            serve_stats[receiver_name]["return_won"] += 1

        # Rally duration tracking
        dur = max(0.0, round(event.end - event.start, 1))
        durations.append(dur)
        if dur > longest_rally_sec:
            longest_rally_sec = dur
            longest_rally_start = event.start

        if dur < 4.0:
            b_key = "short"
        elif dur <= 8.0:
            b_key = "medium"
        else:
            b_key = "long"

        duration_buckets[b_key]["total"] += 1
        if event.winner == player1:
            duration_buckets[b_key]["p1_won"] += 1
        elif event.winner == player2:
            duration_buckets[b_key]["p2_won"] += 1

        # Streak tracking
        if event.winner == player1:
            p1_current_streak += 1
            p2_current_streak = 0
            if p1_current_streak > p1_max_streak:
                p1_max_streak = p1_current_streak
        elif event.winner == player2:
            p2_current_streak += 1
            p1_current_streak = 0
            if p2_current_streak > p2_max_streak:
                p2_max_streak = p2_current_streak

    # Calculate Serve Win %
    for p in [player1, player2]:
        tot = serve_stats[p]["served_total"]
        won = serve_stats[p]["served_won"]
        serve_stats[p]["serve_win_pct"] = round((won / tot) * 100.0, 1) if tot > 0 else 0.0

    # Calculate Duration Win %
    for b in ["short", "medium", "long"]:
        tot = duration_buckets[b]["total"]
        if tot > 0:
            duration_buckets[b]["p1_win_pct"] = round((duration_buckets[b]["p1_won"] / tot) * 100.0, 1)
            duration_buckets[b]["p2_win_pct"] = round((duration_buckets[b]["p2_won"] / tot) * 100.0, 1)

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

    return {
        "first_server": first_server,
        "serve_stats": serve_stats,
        "duration_stats": duration_buckets,
        "momentum": {
            "max_streak": {player1: p1_max_streak, player2: p2_max_streak},
            "avg_duration_sec": avg_duration,
            "longest_rally_sec": longest_rally_sec,
            "longest_rally_start": longest_rally_start
        }
    }

