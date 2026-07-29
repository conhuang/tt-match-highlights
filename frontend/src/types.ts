export interface MatchEvent {
    start: number;
    end: number;
    winner: string;
    timeout_player?: string | null;
    isHighlight: boolean;
    game: number;
    score_before: string;
}

export interface RenderOptions {
    highlights_only: boolean;
    include_scoreboard: boolean;
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
    video_url?: string | null;
}

export interface Match {
    id: string;
    owner_username?: string;
    name: string;
    player1: string;
    player2: string;
    created_at: string;
    video_filename?: string | null;
    original_filename?: string | null;
    rendered_video_filename?: string | null;
    video_url?: string | null;
    rendered_video_url?: string | null;
    events: MatchEvent[];
    renders?: RenderJob[];
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
