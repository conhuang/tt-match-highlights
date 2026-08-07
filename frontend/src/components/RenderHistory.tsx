import React from 'react';
import { RenderJob } from '../types';
import { Play, Download, Trash2, Film, AlertCircle, XCircle, RefreshCw, Star, Zap } from 'lucide-react';

interface RenderHistoryProps {
    renders: RenderJob[];
    onPreviewRender: (renderUrl: string, label: string) => void;
    onDeleteRender: (renderId: string) => void;
    onCancelRender?: (renderId: string) => void;
    activePreviewUrl?: string | null;
    onResetToOriginalVideo?: () => void;
}

function formatDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
}

export const RenderHistory: React.FC<RenderHistoryProps> = ({
    renders,
    onPreviewRender,
    onDeleteRender,
    onCancelRender,
    activePreviewUrl,
    onResetToOriginalVideo
}) => {
    if (!renders || renders.length === 0) {
        return (
            <div className="renders-card card">
                <div className="card-header">
                    <Film size={18} />
                    <h3>Rendered Outputs</h3>
                </div>
                <p className="empty-state">No rendered videos created yet. Click <strong>Render Highlights</strong> to start.</p>
            </div>
        );
    }

    const sortedRenders = [...renders].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    return (
        <div className="renders-card card">
            <div className="card-header">
                <Film size={18} />
                <h3>Rendered Outputs ({renders.length})</h3>
            </div>

            <div className="renders-list">
                {sortedRenders.map((render) => {
                    const isCompleted = render.status === 'completed';
                    const isRendering = render.status === 'rendering' || render.status === 'pending';
                    const isFailed = render.status === 'failed';
                    const isPreviewing = activePreviewUrl === render.video_url;

                    const formattedUtc = render.created_at ? (
                        render.created_at.endsWith('Z') || render.created_at.includes('+')
                            ? render.created_at
                            : `${render.created_at}Z`
                    ) : '';

                    const dateStr = formattedUtc ? new Date(formattedUtc).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit'
                    }) : '';

                    return (
                        <div key={render.id} className={`render-item ${isPreviewing ? 'previewing' : ''}`}>
                            <div className="render-item-top">
                                <div className="render-info">
                                    <div className="render-title-row">
                                        {render.type === 'highlights' ? (
                                            <Star size={14} className="star-active" />
                                        ) : (
                                            <Film size={14} className="accent-icon" />
                                        )}
                                        <span className="render-label">{render.label}</span>
                                        <span className="render-time">{dateStr}</span>
                                    </div>
                                    <span className="render-specs">
                                        {render.options.highlights_only ? 'Highlights Reel' : 'Full Match'} •
                                        {render.options.include_scoreboard ? ' Scoreboard' : ' Clean'} •
                                        {render.options.include_game_cards ? ' Title Cards' : ' Direct Clips'}
                                    </span>
                                </div>

                                <div className="render-status-badge">
                                    {isRendering && (
                                        <span className="status-pill status-rendering">
                                            <RefreshCw size={12} className="spin-icon" /> Rendering
                                        </span>
                                    )}
                                    {isCompleted && (
                                        <div className="render-metrics-group">
                                            {render.video_duration_seconds && render.video_duration_seconds > 0 && (
                                                <span className="duration-pill video-length-pill" title="Actual Output Video Duration">
                                                    <Film size={11} /> {formatDuration(render.video_duration_seconds)}
                                                </span>
                                            )}
                                            {render.render_duration_seconds && render.render_duration_seconds > 0 && (
                                                <span className="duration-pill processing-pill" title="Render Processing Duration">
                                                    <Zap size={11} /> {formatDuration(render.render_duration_seconds)}
                                                </span>
                                            )}
                                            <span className="status-pill status-completed">
                                                Completed
                                            </span>
                                        </div>
                                    )}
                                    {isFailed && (
                                        <span className="status-pill status-failed">
                                            <AlertCircle size={12} /> Failed
                                        </span>
                                    )}
                                </div>
                            </div>

                            {isRendering && (
                                <div className="render-progress-section">
                                    <div className="progress-bar">
                                        <div className="progress-fill" style={{ width: `${render.progress}%` }} />
                                    </div>
                                    <div className="progress-info">
                                        <span className="stage-text">{render.stage}</span>
                                        <span className="percent-text">{render.progress}%</span>
                                    </div>
                                </div>
                            )}

                            {isFailed && render.error && (
                                <div className="error-banner">
                                    {render.error}
                                </div>
                            )}

                            <div className="render-actions">
                                {isRendering && onCancelRender && (
                                    <button
                                        type="button"
                                        className="action-btn cancel-render-btn"
                                        onClick={() => onCancelRender(render.id)}
                                        title="Cancel active rendering job"
                                        style={{ backgroundColor: '#ef4444', color: '#ffffff', borderColor: '#dc2626' }}
                                    >
                                        <XCircle size={13} />
                                        Cancel Render
                                    </button>
                                )}

                                {isCompleted && render.video_url && (
                                    <>
                                        <button
                                            type="button"
                                            className={`action-btn preview-btn ${isPreviewing ? 'active' : ''}`}
                                            onClick={() => {
                                                if (isPreviewing && onResetToOriginalVideo) {
                                                    onResetToOriginalVideo();
                                                } else {
                                                    onPreviewRender(render.video_url!, render.label);
                                                }
                                            }}
                                        >
                                            <Play size={13} />
                                            {isPreviewing ? 'Viewing Output' : 'Preview Video'}
                                        </button>

                                        <a
                                            href={render.video_url}
                                            download={render.filename || 'rendered_highlight.mp4'}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="action-btn download-btn"
                                        >
                                            <Download size={13} />
                                            Download MP4
                                        </a>
                                    </>
                                )}

                                <button
                                    type="button"
                                    className="action-btn delete-render-btn"
                                    onClick={() => onDeleteRender(render.id)}
                                    title="Delete Rendered Video"
                                >
                                    <Trash2 size={13} />
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
