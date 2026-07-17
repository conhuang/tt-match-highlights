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
