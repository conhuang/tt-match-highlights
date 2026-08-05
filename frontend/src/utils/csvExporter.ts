import { Match } from '../types';
import { computeScoresAndGames } from './scoring';

export function determineServerName(
    p1Score: number,
    p2Score: number,
    gameNum: number,
    p1Name: string,
    p2Name: string,
    firstServerGame1: 'player1' | 'player2' = 'player1'
): string {
    const firstInGame = gameNum % 2 !== 0
        ? firstServerGame1
        : (firstServerGame1 === 'player1' ? 'player2' : 'player1');
    const oppositeInGame = firstInGame === 'player1' ? 'player2' : 'player1';

    let serverKey: 'player1' | 'player2';
    if (p1Score >= 10 && p2Score >= 10) {
        const turns = (p1Score + p2Score) - 20;
        serverKey = turns % 2 === 0 ? firstInGame : oppositeInGame;
    } else {
        const turns = Math.floor((p1Score + p2Score) / 2);
        serverKey = turns % 2 === 0 ? firstInGame : oppositeInGame;
    }

    return serverKey === 'player1' ? p1Name : p2Name;
}

export function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    const pad = (num: number) => num.toString().padStart(2, '0');
    return `${pad(m)}:${pad(s)}.${ms}`;
}

export function exportEventsToCSV(match: Match): void {
    const scoredEvents = computeScoresAndGames(match.events, match.player1, match.player2);
    const firstServer = match.first_server || 'player1';

    const headers = [
        'Game',
        'Start Time',
        'End Time',
        'Start Seconds',
        'End Seconds',
        'Duration (s)',
        'Server',
        'Winner',
        'Score Before',
        'Highlight',
        'Timeout'
    ];

    const rows: string[][] = [headers];

    scoredEvents.forEach((event) => {
        const duration = (event.end - event.start).toFixed(2);
        const [p1ScoreStr, p2ScoreStr] = (event.score_before || '0-0').split('-').map(Number);
        const serverName = determineServerName(
            isNaN(p1ScoreStr) ? 0 : p1ScoreStr,
            isNaN(p2ScoreStr) ? 0 : p2ScoreStr,
            event.game || 1,
            match.player1,
            match.player2,
            firstServer
        );

        rows.push([
            (event.game || 1).toString(),
            formatTime(event.start),
            formatTime(event.end),
            event.start.toFixed(2),
            event.end.toFixed(2),
            duration,
            serverName,
            event.winner || 'None',
            event.score_before || '0-0',
            event.isHighlight ? 'Yes' : 'No',
            event.timeout_player || 'None'
        ]);
    });

    const csvContent = rows
        .map((row) =>
            row.map((val) => `"${val.replace(/"/g, '""')}"`).join(',')
        )
        .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    const cleanMatchName = (match.name || 'match_events')
        .replace(/[^a-z0-9_-]/gi, '_')
        .toLowerCase();
    link.href = url;
    link.setAttribute('download', `${cleanMatchName}_events.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
