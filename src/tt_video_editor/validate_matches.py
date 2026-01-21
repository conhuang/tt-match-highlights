#!/usr/bin/env python3
"""Validate table tennis match events JSON files.

Checks:
- Best of 5 matches (first to 3 games)
- Games to 11 points
- Must win by 2 points
"""

import json
import sys
import os
from pathlib import Path


def validate_match(events_path):
    """Validate a match events file and return issues found."""
    with open(events_path) as f:
        events = json.load(f)

    if not events:
        return ["No events found"]

    # Get player names from first event
    all_winners = set(e["winner"] for e in events)
    if len(all_winners) != 2:
        return [f"Expected 2 players, found: {all_winners}"]

    players = sorted(all_winners)
    p1, p2 = players[0], players[1]

    issues = []

    # Track scores
    p1_score = 0
    p2_score = 0
    p1_games = 0
    p2_games = 0
    game_num = 1
    game_history = []

    for i, event in enumerate(events):
        winner = event.get("winner")
        if winner is None:
            continue

        # Add point
        if winner == p1:
            p1_score += 1
        else:
            p2_score += 1

        # Check for game end
        if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
            game_winner = p1 if p1_score > p2_score else p2
            game_history.append(
                {"game": game_num, "score": f"{p1_score}-{p2_score}", "winner": game_winner}
            )

            if game_winner == p1:
                p1_games += 1
            else:
                p2_games += 1

            # Reset for next game
            p1_score = 0
            p2_score = 0
            game_num += 1

            # Check if match is over
            if p1_games >= 3 or p2_games >= 3:
                # Match should be over
                remaining = len(events) - i - 1
                if remaining > 0:
                    issues.append(
                        f"Match ended after event {i + 1} but {remaining} more events exist"
                    )
                break

    # Check final state
    if p1_games < 3 and p2_games < 3:
        issues.append(f"Match incomplete: {p1} has {p1_games} games, {p2} has {p2_games} games")
        if p1_score > 0 or p2_score > 0:
            issues.append(f"Unfinished game {game_num}: {p1_score}-{p2_score}")

    # Summary
    summary = {
        "file": os.path.basename(events_path),
        "players": (p1, p2),
        "total_events": len(events),
        "games": game_history,
        "final_score": f"{p1_games}-{p2_games}",
        "winner": p1 if p1_games > p2_games else p2 if p2_games > p1_games else "TBD",
        "issues": issues,
    }

    return summary


def main():
    # Find all events JSON files
    if len(sys.argv) > 1:
        search_dir = sys.argv[1]
    else:
        search_dir = "."

    json_files = sorted(Path(search_dir).glob("*_events.json"))

    if not json_files:
        print(f"No *_events.json files found in {search_dir}")
        return

    print(f"Found {len(json_files)} match files to validate\n")
    print("=" * 60)

    all_valid = True

    for json_file in json_files:
        result = validate_match(json_file)

        if isinstance(result, list):
            # Just error messages
            print(f"\n❌ {json_file.name}")
            for msg in result:
                print(f"   {msg}")
            all_valid = False
            continue

        # Full result
        has_issues = len(result["issues"]) > 0
        status = "❌" if has_issues else "✅"

        print(f"\n{status} {result['file']}")
        print(f"   Players: {result['players'][0]} vs {result['players'][1]}")
        print(f"   Events: {result['total_events']}")
        print(f"   Games:")
        for game in result["games"]:
            print(f"      Game {game['game']}: {game['score']} → {game['winner']}")
        print(f"   Final: {result['final_score']} ({result['winner']} wins)")

        if has_issues:
            all_valid = False
            print(f"   ⚠️  Issues:")
            for issue in result["issues"]:
                print(f"      - {issue}")

    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All matches are valid!")
    else:
        print("❌ Some matches have issues")


if __name__ == "__main__":
    main()
