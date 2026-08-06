import React from 'react';
import { Match, MatchStats } from '../types';
import { BarChart2, Target, Clock, Flame, Zap, Play, Activity } from 'lucide-react';

interface MatchStatsViewProps {
    match: Match;
    onJumpToTime?: (timeSec: number) => void;
}

export const MatchStatsView: React.FC<MatchStatsViewProps> = ({
    match,
    onJumpToTime
}) => {
    const stats: MatchStats | undefined = match.stats;
    const p1 = match.player1 || 'Player 1';
    const p2 = match.player2 || 'Player 2';

    if (!stats || !match.events || match.events.length === 0) {
        return (
            <div className="match-stats-card card">
                <div className="card-header">
                    <BarChart2 className="accent-icon" size={18} />
                    <h3>Match Analytics & Insights</h3>
                </div>
                <div className="empty-stats-body">
                    <Activity className="empty-icon" size={32} />
                    <p className="empty-state-text">
                        No match points logged yet. Mark clip start times with <strong>E</strong>/<strong>D</strong> and log winners with <strong>1</strong>/<strong>2</strong> to generate real-time serve win ratios, rally duration breakdowns, and momentum analytics.
                    </p>
                </div>
            </div>
        );
    }

    const p1Serve = stats.serve_stats[p1] || { served_total: 0, served_won: 0, serve_win_pct: 0, return_won: 0 };
    const p2Serve = stats.serve_stats[p2] || { served_total: 0, served_won: 0, serve_win_pct: 0, return_won: 0 };

    const p1Streak = stats.momentum.max_streak[p1] || 0;
    const p2Streak = stats.momentum.max_streak[p2] || 0;

    const formatTime = (sec: number) => {
        const mins = Math.floor(sec / 60);
        const secs = Math.floor(sec % 60);
        const pad = (n: number) => n.toString().padStart(2, '0');
        return `${pad(mins)}:${pad(secs)}`;
    };

    return (
        <div className="match-stats-card card">
            <div className="card-header stats-header-row">
                <div className="stats-header-title">
                    <BarChart2 className="accent-icon" size={18} />
                    <h3>Match Analytics & Insights</h3>
                    <span className="stats-live-pill">Live Calculated</span>
                </div>
            </div>

            <div className="stats-content-grid">
                {/* 1. Service & Return Performance */}
                <div className="stats-section-block">
                    <div className="section-title-row">
                        <Target className="section-icon" size={16} />
                        <h4>Service & Return Performance</h4>
                    </div>

                    <div className="serve-grid">
                        {/* Player 1 Block */}
                        <div className="player-serve-card p1-card">
                            <div className="player-meta-row">
                                <span className="player-name">{p1}</span>
                                <span className="stat-pct p1-text">{p1Serve.serve_win_pct}%</span>
                            </div>
                            <div className="progress-track">
                                <div
                                    className="progress-fill p1-bar"
                                    style={{ width: `${Math.min(100, p1Serve.serve_win_pct)}%` }}
                                />
                            </div>
                            <div className="stat-details-row">
                                <span>Serve Points Won: <strong>{p1Serve.served_won} / {p1Serve.served_total}</strong></span>
                                <span>Return Points Won: <strong>{p1Serve.return_won}</strong></span>
                            </div>
                        </div>

                        {/* Player 2 Block */}
                        <div className="player-serve-card p2-card">
                            <div className="player-meta-row">
                                <span className="player-name">{p2}</span>
                                <span className="stat-pct p2-text">{p2Serve.serve_win_pct}%</span>
                            </div>
                            <div className="progress-track">
                                <div
                                    className="progress-fill p2-bar"
                                    style={{ width: `${Math.min(100, p2Serve.serve_win_pct)}%` }}
                                />
                            </div>
                            <div className="stat-details-row">
                                <span>Serve Points Won: <strong>{p2Serve.served_won} / {p2Serve.served_total}</strong></span>
                                <span>Return Points Won: <strong>{p2Serve.return_won}</strong></span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 2. Win Rate by Rally Duration */}
                <div className="stats-section-block">
                    <div className="section-title-row">
                        <Clock className="section-icon" size={16} />
                        <h4>Win Rate by Rally Duration</h4>
                    </div>

                    <div className="duration-buckets-container">
                        {(['short', 'medium', 'long'] as const).map((bKey) => {
                            const bucket = stats.duration_stats[bKey];
                            const total = bucket.total;
                            const p1Pct = bucket.p1_win_pct;
                            const p2Pct = bucket.p2_win_pct;

                            return (
                                <div key={bKey} className="duration-bucket-item">
                                    <div className="bucket-info-col">
                                        <span className="bucket-label-text">{bucket.label}</span>
                                        <span className="bucket-count-badge">{total} rallies</span>
                                    </div>

                                    <div className="duration-meter-wrapper">
                                        <span className="pct-val p1-text">{p1Pct}% ({bucket.p1_won})</span>
                                        <div className="split-progress-bar">
                                            <div
                                                className="split-fill p1-bar"
                                                style={{ width: `${total > 0 ? p1Pct : 50}%` }}
                                            />
                                            <div
                                                className="split-fill p2-bar"
                                                style={{ width: `${total > 0 ? p2Pct : 50}%` }}
                                            />
                                        </div>
                                        <span className="pct-val p2-text">{p2Pct}% ({bucket.p2_won})</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* 3. Match Momentum & Pace */}
                <div className="stats-section-block">
                    <div className="section-title-row">
                        <Zap className="section-icon" size={16} />
                        <h4>Match Momentum & Pace</h4>
                    </div>

                    <div className="momentum-cards-row">
                        {/* Streak Metric */}
                        <div className="momentum-card">
                            <div className="card-top-icon">
                                <Flame size={18} className="flame-icon" />
                            </div>
                            <span className="metric-label">Max Point Streak</span>
                            <div className="metric-values-row">
                                <span className="streak-badge p1-badge">{p1}: <strong>{p1Streak}</strong> pts</span>
                                <span className="streak-badge p2-badge">{p2}: <strong>{p2Streak}</strong> pts</span>
                            </div>
                        </div>

                        {/* Average Duration Metric */}
                        <div className="momentum-card">
                            <div className="card-top-icon">
                                <Clock size={18} className="clock-icon" />
                            </div>
                            <span className="metric-label">Avg Rally Duration</span>
                            <span className="metric-main-val">{stats.momentum.avg_duration_sec}s</span>
                        </div>

                        {/* Longest Rally Metric */}
                        <div className="momentum-card">
                            <div className="card-top-icon">
                                <Activity size={18} className="activity-icon" />
                            </div>
                            <span className="metric-label">Longest Rally</span>
                            <div className="longest-rally-wrapper">
                                <span className="metric-main-val">{stats.momentum.longest_rally_sec}s</span>
                                {onJumpToTime && stats.momentum.longest_rally_start > 0 && (
                                    <button
                                        type="button"
                                        className="jump-rally-btn"
                                        onClick={() => onJumpToTime(stats.momentum.longest_rally_start)}
                                        title="Seek video to longest rally"
                                    >
                                        <Play size={11} />
                                        Jump to {formatTime(stats.momentum.longest_rally_start)}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
