export interface MatchEvent {
    start: number;
    end: number;
    winner?: string | null;
    timeout_player?: string | null;
    isHighlight: boolean;
    game?: number;
}

export interface RenderOptions {
    highlights_only: boolean;
    include_scoreboard: boolean;
    scoreboard_artwork?: 'classic' | 'simple';
    scoreboard_position?: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
    scoreboard_theme?: 'dark-blue' | 'classic-black' | 'vibrant-red' | 'emerald-green' | 'cyber-purple';
    scoreboard_scale?: number;
    scoreboard_sets_color?: 'gold' | 'silver' | 'cyan' | 'green' | 'red';
    scoreboard_sets_bg?: 'transparent' | 'solid-dark' | 'gold-badge' | 'accent-blue' | 'subtle-glass';
    scoreboard_border_style?: 'rounded' | 'sharp';
    scoreboard_font_style?: 'modern' | 'condensed' | 'serif' | 'monospace';
    include_game_cards: boolean;
    cpu_mode: boolean;
}

export interface RenderJob {
    id: string;
    type: 'full_match' | 'highlights';
    label: string;
    filename?: string | null;
    options: RenderOptions;
    status: 'pending' | 'rendering' | 'completed' | 'failed';
    progress: number;
    stage: string;
    error?: string | null;
    created_at: string;
    completed_at?: string | null;
    render_duration_seconds?: number | null;
    video_url?: string | null;
}

export interface PlayerServeStat {
    served_total: number;
    served_won: number;
    serve_win_pct: number;
    return_won: number;
}

export interface DurationBucketStat {
    total: number;
    p1_won: number;
    p2_won: number;
    p1_win_pct: number;
    p2_win_pct: number;
    label: string;
}

export interface MatchStats {
    first_server: 'player1' | 'player2';
    serve_stats: Record<string, PlayerServeStat>;
    duration_stats: {
        short: DurationBucketStat;
        medium: DurationBucketStat;
        long: DurationBucketStat;
    };
    momentum: {
        max_streak: Record<string, number>;
        avg_duration_sec: number;
        longest_rally_sec: number;
        longest_rally_start: number;
    };
}

export interface Match {
    id: string;
    owner_username?: string;
    name: string;
    player1: string;
    player2: string;
    first_server?: 'player1' | 'player2';
    created_at: string;
    video_filename?: string | null;
    original_filename?: string | null;
    rendered_video_filename?: string | null;
    video_url?: string | null;
    rendered_video_url?: string | null;
    events: MatchEvent[];
    renders?: RenderJob[];
    stats?: MatchStats;
    fps?: number | null;
    duration?: number | null;
    width?: number | null;
    height?: number | null;
}

export interface UploadPart {
    PartNumber: number;
    UploadUrl: string;
}

export interface InitializeResponse {
    upload_id: string;
    parts: UploadPart[];
    unique_filename: string;
    original_filename: string;
}

export interface CreateMatchInput {
    name: string;
    player1: string;
    player2: string;
}

export interface ResumeSession {
    matchId: string;
    uploadId: string;
    originalFilename: string;
    fileSize: number;
    matchName: string;
    player1: string;
    player2: string;
    parts: UploadPart[];
}
