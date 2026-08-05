import { MatchEvent } from '../types';

export interface ScoredMatchEvent extends MatchEvent {
    game: number;
    score_before: string;
}

/**
 * Sorts events chronologically by start timestamp and dynamically computes 
 * running game scores (score_before) and game numbers for each event based on 
 * ITTF Table Tennis rules (11-point games, win by 2, reset to 0-0).
 */
export function computeScoresAndGames(
    events: MatchEvent[],
    player1: string,
    player2: string
): ScoredMatchEvent[] {
    const sorted = [...events].sort((a, b) => a.start - b.start || a.end - b.end);

    let p1Score = 0;
    let p2Score = 0;
    let currentGame = 1;

    return sorted.map((event) => {
        const score_before = `${p1Score}-${p2Score}`;
        const game = currentGame;

        if (event.winner === player1) {
            p1Score += 1;
        } else if (event.winner === player2) {
            p2Score += 1;
        }

        if ((p1Score >= 11 || p2Score >= 11) && Math.abs(p1Score - p2Score) >= 2) {
            p1Score = 0;
            p2Score = 0;
            currentGame += 1;
        }

        return {
            ...event,
            game,
            score_before
        };
    });
}
