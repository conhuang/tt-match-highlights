import { MatchEvent } from '../types';

export interface ScoredMatchEvent extends MatchEvent {
    game: number;
    score_before: string;
    score_after: string;
}

/**
 * Sorts events chronologically by start timestamp and dynamically computes 
 * running game scores (score_before and score_after) and game numbers for each event based on 
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

        const score_after = `${p1Score}-${p2Score}`;

        if ((p1Score >= 11 || p2Score >= 11) && Math.abs(p1Score - p2Score) >= 2) {
            p1Score = 0;
            p2Score = 0;
            currentGame += 1;
        }

        return {
            ...event,
            game,
            score_before,
            score_after
        };
    });
}

/**
 * Determines whether 'player1' or 'player2' is serving according to official ITTF rules.
 */
export function determineServer(
    p1Score: number,
    p2Score: number,
    gameNum: number,
    firstServerGame1: 'player1' | 'player2' = 'player1'
): 'player1' | 'player2' {
    const firstInGame = gameNum % 2 !== 0 ? firstServerGame1 : (firstServerGame1 === 'player1' ? 'player2' : 'player1');
    const oppositeInGame = firstInGame === 'player1' ? 'player2' : 'player1';

    if (p1Score >= 10 && p2Score >= 10) {
        const turns = (p1Score + p2Score) - 20;
        return turns % 2 === 0 ? firstInGame : oppositeInGame;
    } else {
        const turns = Math.floor((p1Score + p2Score) / 2);
        return turns % 2 === 0 ? firstInGame : oppositeInGame;
    }
}

/**
 * Computes live match analytics matching backend scoring:
 * - Service & return win ratios
 * - Rally duration breakdown (0-6s short, 6-10s medium, 10s+ long)
 * - Serve ratio and self-serve win rate per rally length
 * - Momentum & streaks
 */
export function computeMatchAnalytics(
    events: MatchEvent[],
    player1: string,
    player2: string,
    firstServer: 'player1' | 'player2' = 'player1'
): import('../types').MatchStats {
    const sorted = [...events].sort((a, b) => a.start - b.start || a.end - b.end);

    const serve_stats: Record<string, import('../types').PlayerServeStat> = {
        [player1]: { served_total: 0, served_won: 0, serve_win_pct: 0, return_won: 0 },
        [player2]: { served_total: 0, served_won: 0, serve_win_pct: 0, return_won: 0 }
    };

    const duration_stats: import('../types').MatchStats['duration_stats'] = {
        short: {
            total: 0,
            p1_won: 0,
            p2_won: 0,
            p1_win_pct: 0,
            p2_win_pct: 0,
            p1_served: 0,
            p2_served: 0,
            p1_serve_pct: 0,
            p2_serve_pct: 0,
            p1_self_serve_won: 0,
            p1_self_serve_win_pct: 0,
            p2_self_serve_won: 0,
            p2_self_serve_win_pct: 0,
            label: '0 - 6s (Short Rally)'
        },
        medium: {
            total: 0,
            p1_won: 0,
            p2_won: 0,
            p1_win_pct: 0,
            p2_win_pct: 0,
            p1_served: 0,
            p2_served: 0,
            p1_serve_pct: 0,
            p2_serve_pct: 0,
            p1_self_serve_won: 0,
            p1_self_serve_win_pct: 0,
            p2_self_serve_won: 0,
            p2_self_serve_win_pct: 0,
            label: '6 - 10s (Medium Rally)'
        },
        long: {
            total: 0,
            p1_won: 0,
            p2_won: 0,
            p1_win_pct: 0,
            p2_win_pct: 0,
            p1_served: 0,
            p2_served: 0,
            p1_serve_pct: 0,
            p2_serve_pct: 0,
            p1_self_serve_won: 0,
            p1_self_serve_win_pct: 0,
            p2_self_serve_won: 0,
            p2_self_serve_win_pct: 0,
            label: '10s+ (Long Rally)'
        }
    };

    let p1Streak = 0;
    let p1MaxStreak = 0;
    let p2Streak = 0;
    let p2MaxStreak = 0;

    const durations: number[] = [];
    let longestRallySec = 0;
    let longestRallyStart = 0;

    let p1Score = 0;
    let p2Score = 0;
    let currentGame = 1;

    for (const event of sorted) {
        if (!event.winner) continue;

        const serverKey = determineServer(p1Score, p2Score, currentGame, firstServer);
        const serverName = serverKey === 'player1' ? player1 : player2;
        const receiverName = serverKey === 'player1' ? player2 : player1;

        if (serve_stats[serverName]) {
            serve_stats[serverName].served_total += 1;
            if (event.winner === serverName) {
                serve_stats[serverName].served_won += 1;
            } else if (serve_stats[receiverName]) {
                serve_stats[receiverName].return_won += 1;
            }
        }

        const dur = Math.max(0, Math.round((event.end - event.start) * 10) / 10);
        durations.push(dur);
        if (dur > longestRallySec) {
            longestRallySec = dur;
            longestRallyStart = event.start;
        }

        const bKey: 'short' | 'medium' | 'long' = dur <= 6.0 ? 'short' : dur <= 10.0 ? 'medium' : 'long';
        duration_stats[bKey].total += 1;

        if (event.winner === player1) {
            duration_stats[bKey].p1_won += 1;
            p1Score += 1;
            p1Streak += 1;
            p2Streak = 0;
            if (p1Streak > p1MaxStreak) p1MaxStreak = p1Streak;
        } else if (event.winner === player2) {
            duration_stats[bKey].p2_won += 1;
            p2Score += 1;
            p2Streak += 1;
            p1Streak = 0;
            if (p2Streak > p2MaxStreak) p2MaxStreak = p2Streak;
        }

        if (serverName === player1) {
            duration_stats[bKey].p1_served += 1;
            if (event.winner === player1) {
                duration_stats[bKey].p1_self_serve_won += 1;
            }
        } else if (serverName === player2) {
            duration_stats[bKey].p2_served += 1;
            if (event.winner === player2) {
                duration_stats[bKey].p2_self_serve_won += 1;
            }
        }

        if ((p1Score >= 11 || p2Score >= 11) && Math.abs(p1Score - p2Score) >= 2) {
            p1Score = 0;
            p2Score = 0;
            currentGame += 1;
        }
    }

    for (const p of [player1, player2]) {
        if (serve_stats[p]) {
            const tot = serve_stats[p].served_total;
            serve_stats[p].serve_win_pct = tot > 0 ? Math.round((serve_stats[p].served_won / tot) * 1000) / 10 : 0;
        }
    }

    for (const b of ['short', 'medium', 'long'] as const) {
        const tot = duration_stats[b].total;
        if (tot > 0) {
            duration_stats[b].p1_win_pct = Math.round((duration_stats[b].p1_won / tot) * 1000) / 10;
            duration_stats[b].p2_win_pct = Math.round((duration_stats[b].p2_won / tot) * 1000) / 10;
            duration_stats[b].p1_serve_pct = Math.round((duration_stats[b].p1_served / tot) * 1000) / 10;
            duration_stats[b].p2_serve_pct = Math.round((duration_stats[b].p2_served / tot) * 1000) / 10;
        }
        const p1s = duration_stats[b].p1_served;
        if (p1s > 0) {
            duration_stats[b].p1_self_serve_win_pct = Math.round((duration_stats[b].p1_self_serve_won / p1s) * 1000) / 10;
        }
        const p2s = duration_stats[b].p2_served;
        if (p2s > 0) {
            duration_stats[b].p2_self_serve_win_pct = Math.round((duration_stats[b].p2_self_serve_won / p2s) * 1000) / 10;
        }
    }

    const avgDur = durations.length > 0 ? Math.round((durations.reduce((a, b) => a + b, 0) / durations.length) * 10) / 10 : 0;

    return {
        first_server: firstServer,
        serve_stats,
        duration_stats,
        momentum: {
            max_streak: { [player1]: p1MaxStreak, [player2]: p2MaxStreak },
            avg_duration_sec: avgDur,
            longest_rally_sec: longestRallySec,
            longest_rally_start: longestRallyStart
        }
    };
}
