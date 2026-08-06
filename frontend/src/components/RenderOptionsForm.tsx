import React, { useState } from 'react';
import { RenderOptions } from '../types';
import { Film, CheckSquare, Square, Palette, Move, Maximize2, Trophy, Type, CornerUpRight, Layout, ChevronDown, ChevronUp, Sliders, Layers } from 'lucide-react';
import { Button } from './ui';

interface RenderOptionsFormProps {
    onSubmit: (type: 'full_match' | 'highlights', label: string, options: RenderOptions) => void;
    hasHighlights: boolean;
    isRendering: boolean;
    player1?: string;
    player2?: string;
}

export type ScoreboardArtwork = 'classic' | 'simple';
export type ScoreboardPosition = 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
export type ScoreboardTheme = 'dark-blue' | 'classic-black' | 'vibrant-red' | 'emerald-green' | 'cyber-purple';
export type ScoreboardSetsColor = 'gold' | 'silver' | 'cyan' | 'green' | 'red';
export type ScoreboardSetsBg = 'transparent' | 'solid-dark' | 'gold-badge' | 'accent-blue' | 'subtle-glass';
export type ScoreboardBorderStyle = 'rounded' | 'sharp';
export type ScoreboardFontStyle = 'modern' | 'condensed' | 'serif' | 'monospace';

export const RenderOptionsForm: React.FC<RenderOptionsFormProps> = ({
    onSubmit,
    hasHighlights,
    isRendering,
    player1,
    player2
}) => {
    const [isExpanded, setIsExpanded] = useState<boolean>(false);
    const [isFineTuneExpanded, setIsFineTuneExpanded] = useState<boolean>(false);
    const [renderType, setRenderType] = useState<'full_match' | 'highlights'>('full_match');
    const [label, setLabel] = useState<string>('Full Scored Match');
    const [includeScoreboard, setIncludeScoreboard] = useState<boolean>(true);
    const [scoreboardArtwork, setScoreboardArtwork] = useState<ScoreboardArtwork>('classic');
    const [scoreboardPosition, setScoreboardPosition] = useState<ScoreboardPosition>('bottom-left');
    const [scoreboardTheme, setScoreboardTheme] = useState<ScoreboardTheme>('dark-blue');
    const [scoreboardScale, setScoreboardScale] = useState<number>(1.0);
    const [scoreboardSetsColor, setScoreboardSetsColor] = useState<ScoreboardSetsColor>('gold');
    const [scoreboardSetsBg, setScoreboardSetsBg] = useState<ScoreboardSetsBg>('transparent');
    const [scoreboardBorderStyle, setScoreboardBorderStyle] = useState<ScoreboardBorderStyle>('rounded');
    const [scoreboardFontStyle, setScoreboardFontStyle] = useState<ScoreboardFontStyle>('modern');
    const [includeGameCards, setIncludeGameCards] = useState<boolean>(true);
    const [cpuMode, setCpuMode] = useState<boolean>(true);

    const ARTWORK_CONFIGS: Record<ScoreboardArtwork, { name: string; desc: string }> = {
        'classic': {
            name: 'Classic',
            desc: 'Multi-panel broadcast layout with left accent stripe & serve triangle'
        },
        'simple': {
            name: 'Simple',
            desc: 'Unified single rounded rectangle with inner grid divider lines'
        }
    };

    const THEME_PREVIEWS: Record<ScoreboardTheme, { name: string; nameBg: string; setBg: string; pointBg: string; accentColor: string; fill: string; outline: string }> = {
        'dark-blue': {
            name: 'Dark Blue',
            nameBg: 'rgba(18, 28, 50, 0.95)',
            setBg: 'rgba(40, 55, 85, 0.95)',
            pointBg: 'rgba(30, 42, 68, 0.95)',
            accentColor: '#37a0aa',
            fill: 'rgba(10, 25, 60, 0.95)',
            outline: 'rgba(255, 255, 255, 0.2)'
        },
        'classic-black': {
            name: 'Classic Black',
            nameBg: 'rgba(25, 25, 30, 0.95)',
            setBg: 'rgba(42, 42, 50, 0.95)',
            pointBg: 'rgba(15, 15, 18, 0.95)',
            accentColor: '#b4becd',
            fill: 'rgba(15, 15, 18, 0.95)',
            outline: 'rgba(255, 255, 255, 0.25)'
        },
        'vibrant-red': {
            name: 'Crimson Red',
            nameBg: 'rgba(80, 12, 18, 0.95)',
            setBg: 'rgba(115, 20, 30, 0.95)',
            pointBg: 'rgba(50, 8, 12, 0.95)',
            accentColor: '#ff6464',
            fill: 'rgba(80, 12, 18, 0.95)',
            outline: 'rgba(255, 120, 120, 0.3)'
        },
        'emerald-green': {
            name: 'Emerald Green',
            nameBg: 'rgba(8, 48, 30, 0.95)',
            setBg: 'rgba(15, 72, 45, 0.95)',
            pointBg: 'rgba(6, 32, 20, 0.95)',
            accentColor: '#32e68c',
            fill: 'rgba(8, 48, 30, 0.95)',
            outline: 'rgba(100, 220, 160, 0.3)'
        },
        'cyber-purple': {
            name: 'Cyber Purple',
            nameBg: 'rgba(45, 15, 75, 0.95)',
            setBg: 'rgba(70, 22, 112, 0.95)',
            pointBg: 'rgba(28, 10, 50, 0.95)',
            accentColor: '#d250ff',
            fill: 'rgba(45, 15, 75, 0.95)',
            outline: 'rgba(180, 100, 255, 0.3)'
        }
    };

    const SETS_COLOR_PREVIEWS: Record<ScoreboardSetsColor, { name: string; hex: string }> = {
        'gold': { name: 'Gold', hex: '#ffc832' },
        'silver': { name: 'Silver', hex: '#dcdcdc' },
        'cyan': { name: 'Cyan', hex: '#37a0aa' },
        'green': { name: 'Neon Green', hex: '#32e68c' },
        'red': { name: 'Coral Red', hex: '#ff6464' }
    };

    const SETS_BG_PREVIEWS: Record<ScoreboardSetsBg, { name: string; bg: string }> = {
        'transparent': { name: 'Transparent', bg: 'transparent' },
        'solid-dark': { name: 'Dark Tint', bg: 'rgba(0, 0, 0, 0.55)' },
        'gold-badge': { name: 'Gold Badge', bg: 'rgba(180, 135, 10, 0.45)' },
        'accent-blue': { name: 'Accent Blue', bg: 'rgba(30, 80, 180, 0.45)' },
        'subtle-glass': { name: 'Subtle Glass', bg: 'rgba(255, 255, 255, 0.15)' }
    };

    const FONT_PREVIEWS: Record<ScoreboardFontStyle, { name: string; fontFamily: string }> = {
        'modern': { name: 'Modern', fontFamily: 'system-ui, sans-serif' },
        'condensed': { name: 'Impact', fontFamily: 'Impact, sans-serif' },
        'serif': { name: 'Serif', fontFamily: 'Georgia, serif' },
        'monospace': { name: 'Mono', fontFamily: 'Courier New, monospace' }
    };

    const POSITION_PREVIEWS: Array<{ label: string; val: ScoreboardPosition }> = [
        { label: 'Bottom Left', val: 'bottom-left' },
        { label: 'Bottom Right', val: 'bottom-right' },
        { label: 'Top Left', val: 'top-left' },
        { label: 'Top Right', val: 'top-right' }
    ];

    const p1Name = player1 || 'Jonathan Li';
    const p2Name = player2 || 'Simeon Martin';
    const maxNameLen = Math.max(p1Name.length, p2Name.length);
    const nameMinWidth = `${Math.max(65, Math.min(maxNameLen * 7.5, 140))}px`;

    const activeTheme = THEME_PREVIEWS[scoreboardTheme];
    const resolvedSetBg = scoreboardSetsBg !== 'transparent'
        ? SETS_BG_PREVIEWS[scoreboardSetsBg].bg
        : activeTheme.setBg;

    const handleTypeChange = (type: 'full_match' | 'highlights') => {
        setRenderType(type);
        setLabel(type === 'highlights' ? 'Highlights Reel' : 'Full Scored Match');
        if (type === 'highlights') {
            setIncludeGameCards(false);
        } else {
            setIncludeGameCards(true);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit(renderType, label, {
            highlights_only: renderType === 'highlights',
            include_scoreboard: includeScoreboard,
            scoreboard_artwork: scoreboardArtwork,
            scoreboard_position: scoreboardPosition,
            scoreboard_theme: scoreboardTheme,
            scoreboard_scale: scoreboardScale,
            scoreboard_sets_color: scoreboardSetsColor,
            scoreboard_sets_bg: scoreboardSetsBg,
            scoreboard_border_style: scoreboardBorderStyle,
            scoreboard_font_style: scoreboardFontStyle,
            include_game_cards: includeGameCards,
            cpu_mode: cpuMode
        });
    };

    return (
        <section className="render-options-section card">
            <div className="section-title-row clickable" onClick={() => setIsExpanded(!isExpanded)}>
                <div className="title-left">
                    <Film className="accent-icon" size={18} />
                    <h3>Render Options & Scoreboard</h3>
                </div>
                <div className="title-right-controls">
                    {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>
            </div>

            <form onSubmit={handleSubmit} className="render-inline-form">
                {!isExpanded ? (
                    <div className="compact-action-row">
                        <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            icon={<Sliders size={14} />}
                            onClick={() => setIsExpanded(true)}
                        >
                            Customize Options
                        </Button>

                        <Button
                            type="submit"
                            variant="render"
                            size="sm"
                            icon={<Film size={15} />}
                            disabled={isRendering || (renderType === 'highlights' && !hasHighlights)}
                        >
                            {isRendering ? 'Rendering...' : '🎬 Start Video Render'}
                        </Button>
                    </div>
                ) : (
                    <>
                        <div className="form-group">
                            <label className="group-label">Render Mode</label>
                            <div className="mode-selector-grid">
                                <button
                                    type="button"
                                    className={`mode-card ${renderType === 'full_match' ? 'active' : ''}`}
                                    onClick={() => handleTypeChange('full_match')}
                                >
                                    <div className="mode-title">Full Scored Match</div>
                                    <div className="mode-desc">Includes all rallies with live score overlay</div>
                                </button>

                                <button
                                    type="button"
                                    className={`mode-card ${renderType === 'highlights' ? 'active' : ''}`}
                                    onClick={() => handleTypeChange('highlights')}
                                >
                                    <div className="mode-title">⭐ Highlights Reel</div>
                                    <div className="mode-desc">Compilation of starred highlight points</div>
                                </button>
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="inline-render-label" className="group-label">Render Title Label</label>
                            <input
                                type="text"
                                id="inline-render-label"
                                value={label}
                                onChange={(e) => setLabel(e.target.value)}
                                className="input-field"
                                placeholder="e.g. 1080p Final Render"
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label className="group-label">Scoreboard Overlay Settings</label>
                            <div className="toggles-list">
                                <label className="toggle-item" onClick={() => setIncludeScoreboard(!includeScoreboard)}>
                                    {includeScoreboard ? <CheckSquare className="checkbox-icon active" size={18} /> : <Square className="checkbox-icon" size={18} />}
                                    <div className="toggle-text">
                                        <span className="toggle-title">Include Scoreboard Overlay</span>
                                        <span className="toggle-desc">Render dynamic broadcast scoreboard overlay</span>
                                    </div>
                                </label>

                                {/* Scoreboard Customization Sub-Panel */}
                                {includeScoreboard && (
                                    <div className="scoreboard-customizer-panel">
                                        {/* Artwork Style Design Selector */}
                                        <div className="customizer-block full-width">
                                            <div className="block-title">
                                                <Layers size={14} />
                                                <span>Scoreboard Style</span>
                                            </div>
                                            <div className="preset-cards-grid">
                                                {(Object.keys(ARTWORK_CONFIGS) as ScoreboardArtwork[]).map((aKey) => {
                                                    const aCfg = ARTWORK_CONFIGS[aKey];
                                                    return (
                                                        <button
                                                            key={aKey}
                                                            type="button"
                                                            className={`preset-card-item ${scoreboardArtwork === aKey ? 'active' : ''}`}
                                                            onClick={() => setScoreboardArtwork(aKey)}
                                                        >
                                                            <div className="preset-card-title">{aCfg.name}</div>
                                                            <div className="preset-card-desc">{aCfg.desc}</div>
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>

                                        <div className="customizer-header" onClick={() => setIsFineTuneExpanded(!isFineTuneExpanded)}>
                                            <div className="customizer-header-title">
                                                <Palette size={15} />
                                                <span>Fine-Tune Appearance</span>
                                            </div>
                                            {isFineTuneExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                        </div>

                                        {isFineTuneExpanded && (
                                            <div className="customizer-grid">
                                                {/* Position Selector */}
                                                <div className="customizer-block">
                                                    <div className="block-title">
                                                        <Move size={13} />
                                                        <span>Position</span>
                                                    </div>
                                                    <div className="theme-chips-list">
                                                        {POSITION_PREVIEWS.map((posOpt) => (
                                                            <button
                                                                key={posOpt.val}
                                                                type="button"
                                                                className={`theme-chip ${scoreboardPosition === posOpt.val ? 'active' : ''}`}
                                                                onClick={() => setScoreboardPosition(posOpt.val)}
                                                            >
                                                                <span>{posOpt.label}</span>
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>

                                                {/* Theme Selector */}
                                                <div className="customizer-block">
                                                    <div className="block-title">
                                                        <Palette size={13} />
                                                        <span>Card Theme</span>
                                                    </div>
                                                    <div className="theme-chips-list">
                                                        {(Object.keys(THEME_PREVIEWS) as ScoreboardTheme[]).map((tKey) => {
                                                            const themeInfo = THEME_PREVIEWS[tKey];
                                                            return (
                                                                <button
                                                                    key={tKey}
                                                                    type="button"
                                                                    className={`theme-chip ${scoreboardTheme === tKey ? 'active' : ''}`}
                                                                    onClick={() => setScoreboardTheme(tKey)}
                                                                >
                                                                    <span className="color-dot" style={{ backgroundColor: themeInfo.accentColor, borderColor: themeInfo.outline }} />
                                                                    <span>{themeInfo.name}</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </div>

                                                {/* Set Score Color Selector */}
                                                <div className="customizer-block">
                                                    <div className="block-title">
                                                        <Trophy size={13} />
                                                        <span>Set Score Color</span>
                                                    </div>
                                                    <div className="theme-chips-list">
                                                        {(Object.keys(SETS_COLOR_PREVIEWS) as ScoreboardSetsColor[]).map((cKey) => {
                                                            const colorInfo = SETS_COLOR_PREVIEWS[cKey];
                                                            return (
                                                                <button
                                                                    key={cKey}
                                                                    type="button"
                                                                    className={`theme-chip ${scoreboardSetsColor === cKey ? 'active' : ''}`}
                                                                    onClick={() => setScoreboardSetsColor(cKey)}
                                                                >
                                                                    <span className="color-dot" style={{ backgroundColor: colorInfo.hex }} />
                                                                    <span>{colorInfo.name}</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </div>

                                                {/* Set Column Fill Selector */}
                                                {scoreboardArtwork === 'classic' && (
                                                    <div className="customizer-block">
                                                        <div className="block-title">
                                                            <Layout size={13} />
                                                            <span>Set Column Fill</span>
                                                        </div>
                                                        <div className="theme-chips-list">
                                                            {(Object.keys(SETS_BG_PREVIEWS) as ScoreboardSetsBg[]).map((bgKey) => {
                                                                const bgInfo = SETS_BG_PREVIEWS[bgKey];
                                                                return (
                                                                    <button
                                                                        key={bgKey}
                                                                        type="button"
                                                                        className={`theme-chip ${scoreboardSetsBg === bgKey ? 'active' : ''}`}
                                                                        onClick={() => setScoreboardSetsBg(bgKey)}
                                                                    >
                                                                        <span className="color-dot" style={{ backgroundColor: bgInfo.bg === 'transparent' ? activeTheme.setBg : bgInfo.bg }} />
                                                                        <span>{bgInfo.name}</span>
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Corners / Edge Style */}
                                                <div className="customizer-block">
                                                    <div className="block-title">
                                                        <CornerUpRight size={13} />
                                                        <span>Card Corners</span>
                                                    </div>
                                                    <div className="scale-pills">
                                                        {[
                                                            { label: 'Rounded (10px)', val: 'rounded' as ScoreboardBorderStyle },
                                                            { label: 'Sharp (0px)', val: 'sharp' as ScoreboardBorderStyle }
                                                        ].map((styleOpt) => (
                                                            <button
                                                                key={styleOpt.val}
                                                                type="button"
                                                                className={`scale-pill ${scoreboardBorderStyle === styleOpt.val ? 'active' : ''}`}
                                                                onClick={() => setScoreboardBorderStyle(styleOpt.val)}
                                                            >
                                                                {styleOpt.label}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>

                                                {/* Font Family Selector */}
                                                <div className="customizer-block">
                                                    <div className="block-title">
                                                        <Type size={13} />
                                                        <span>Typography Font</span>
                                                    </div>
                                                    <div className="theme-chips-list">
                                                        {(Object.keys(FONT_PREVIEWS) as ScoreboardFontStyle[]).map((fKey) => {
                                                            const fontInfo = FONT_PREVIEWS[fKey];
                                                            return (
                                                                <button
                                                                    key={fKey}
                                                                    type="button"
                                                                    className={`theme-chip ${scoreboardFontStyle === fKey ? 'active' : ''}`}
                                                                    onClick={() => setScoreboardFontStyle(fKey)}
                                                                    style={{ fontFamily: fontInfo.fontFamily }}
                                                                >
                                                                    <span>{fontInfo.name}</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </div>

                                                {/* Scale Selector */}
                                                <div className="customizer-block">
                                                    <div className="block-title">
                                                        <Maximize2 size={13} />
                                                        <span>Size / Scale</span>
                                                    </div>
                                                    <div className="scale-pills">
                                                        {[
                                                            { label: 'Compact (80%)', val: 0.8 },
                                                            { label: 'Standard (100%)', val: 1.0 },
                                                            { label: 'Large (120%)', val: 1.2 }
                                                        ].map((scaleOpt) => (
                                                            <button
                                                                key={scaleOpt.val}
                                                                type="button"
                                                                className={`scale-pill ${scoreboardScale === scaleOpt.val ? 'active' : ''}`}
                                                                onClick={() => setScoreboardScale(scaleOpt.val)}
                                                            >
                                                                {scaleOpt.label}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* High-Fidelity Live Mini Preview Canvas */}
                                        <div className="scoreboard-preview-canvas">
                                            <div className="preview-canvas-label">Live Broadcast Preview ({ARTWORK_CONFIGS[scoreboardArtwork].name})</div>
                                            
                                            {scoreboardArtwork === 'classic' ? (
                                                <div className={`mini-scoreboard-wtt mini-${scoreboardPosition}`} style={{
                                                    borderRadius: scoreboardBorderStyle === 'sharp' ? '0px' : '5px',
                                                    fontFamily: FONT_PREVIEWS[scoreboardFontStyle].fontFamily,
                                                    transform: `scale(${0.85 * scoreboardScale})`
                                                }}>
                                                    <div className="wtt-accent-stripe" style={{ backgroundColor: activeTheme.accentColor }} />
                                                    <div className="wtt-content-body">
                                                        <div className="wtt-row">
                                                            <div className="wtt-name-cell" style={{ backgroundColor: activeTheme.nameBg }}>
                                                                <span className="wtt-name" style={{ minWidth: nameMinWidth }}>{p1Name}</span>
                                                                <span className="wtt-timeout">T</span>
                                                            </div>
                                                            <span className="wtt-sets" style={{ color: SETS_COLOR_PREVIEWS[scoreboardSetsColor].hex, backgroundColor: resolvedSetBg }}>2</span>
                                                            <span className="wtt-pts" style={{ backgroundColor: activeTheme.pointBg }}>8</span>
                                                        </div>
                                                        <div className="wtt-row">
                                                            <div className="wtt-name-cell" style={{ backgroundColor: activeTheme.nameBg }}>
                                                                <span className="wtt-name" style={{ minWidth: nameMinWidth }}>{p2Name}</span>
                                                                <span className="wtt-timeout invisible">T</span>
                                                            </div>
                                                            <span className="wtt-sets" style={{ color: SETS_COLOR_PREVIEWS[scoreboardSetsColor].hex, backgroundColor: resolvedSetBg }}>0</span>
                                                            <span className="wtt-pts" style={{ backgroundColor: activeTheme.pointBg }}>9</span>
                                                        </div>
                                                    </div>
                                                    <div className="wtt-serve-triangle" style={{ color: activeTheme.accentColor }} title="Serve Indicator (◀)">◀</div>
                                                </div>
                                            ) : (
                                                <div className={`mini-scoreboard-classic mini-${scoreboardPosition}`} style={{
                                                    backgroundColor: activeTheme.fill,
                                                    borderColor: activeTheme.outline,
                                                    borderRadius: scoreboardBorderStyle === 'sharp' ? '0px' : '6px',
                                                    fontFamily: FONT_PREVIEWS[scoreboardFontStyle].fontFamily,
                                                    transform: `scale(${0.85 * scoreboardScale})`
                                                }}>
                                                    <div className="classic-row">
                                                        <span className="classic-name" style={{ minWidth: nameMinWidth }}>{p1Name}</span>
                                                        <span className="classic-timeout">T</span>
                                                        <span className="classic-sets" style={{ color: SETS_COLOR_PREVIEWS[scoreboardSetsColor].hex }}>2</span>
                                                        <span className="classic-pts">8</span>
                                                    </div>
                                                    <div className="classic-row">
                                                        <span className="classic-name" style={{ minWidth: nameMinWidth }}>{p2Name}</span>
                                                        <span className="classic-timeout invisible">T</span>
                                                        <span className="classic-sets" style={{ color: SETS_COLOR_PREVIEWS[scoreboardSetsColor].hex }}>0</span>
                                                        <span className="classic-pts">9</span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                <label className="toggle-item" onClick={() => setIncludeGameCards(!includeGameCards)}>
                                    {includeGameCards ? <CheckSquare className="checkbox-icon active" size={18} /> : <Square className="checkbox-icon" size={18} />}
                                    <div className="toggle-text">
                                        <span className="toggle-title">Include Inter-Game Title Cards</span>
                                        <span className="toggle-desc">Insert 2-second "Game 1", "Game 2" cards between sets</span>
                                    </div>
                                </label>

                                <label className="toggle-item" onClick={() => setCpuMode(!cpuMode)}>
                                    {cpuMode ? <CheckSquare className="checkbox-icon active" size={18} /> : <Square className="checkbox-icon" size={18} />}
                                    <div className="toggle-text">
                                        <span className="toggle-title">Software CPU Encoder (libx264)</span>
                                        <span className="toggle-desc">Maximum compatibility & reliable video quality</span>
                                    </div>
                                </label>
                            </div>
                        </div>

                        {renderType === 'highlights' && !hasHighlights && (
                            <div className="warning-banner">
                                ⚠️ No points are currently tagged with ⭐ Highlight in this match. Star at least one point before rendering a Highlights Reel.
                            </div>
                        )}

                        <div className="inline-render-actions">
                            <Button
                                type="submit"
                                variant="render"
                                size="lg"
                                icon={<Film size={18} />}
                                disabled={isRendering || (renderType === 'highlights' && !hasHighlights)}
                                className="start-render-btn-large"
                            >
                                {isRendering ? 'Starting Render Job...' : '🎬 Start Video Render'}
                            </Button>
                        </div>
                    </>
                )}
            </form>
        </section>
    );
};
