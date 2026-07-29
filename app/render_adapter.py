import os
import sys
import shutil
import subprocess
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Automatically resolve src/ directory for tt_video_editor package
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from app.models import Match, RenderJob

logger = logging.getLogger(__name__)

def update_render_job_status(
    match_id: str,
    render_id: str,
    db_repo,
    status: str,
    progress: int,
    stage: str,
    error: Optional[str] = None,
    filename: Optional[str] = None,
    completed_at: Optional[str] = None
):
    """Helper function to update a specific render job inside a match's renders array."""
    record = db_repo.get_match(match_id)
    if not record:
        return
    
    match = Match.model_validate(record)
    updated_renders = []
    for r in match.renders:
        if r.id == render_id:
            r.status = status
            r.progress = progress
            r.stage = stage
            r.error = error
            if filename:
                r.filename = filename
            if completed_at:
                r.completed_at = completed_at
        updated_renders.append(r.model_dump())
    
    match_dict = match.model_dump()
    match_dict["renders"] = updated_renders
    db_repo.create_match(match_dict)


def execute_render_job(
    match_id: str,
    render_id: str,
    db_repo,
    storage_provider
):
    """
    Background worker task executing video rendering for a match.
    Enforces 1080p max resolution capping, '-preset superfast', color space preservation/HDR tone-mapping,
    and positive render option signals (include_scoreboard, include_game_cards).
    """
    record = db_repo.get_match(match_id)
    if not record:
        logger.error(f"Render failed: Match {match_id} not found.")
        return

    match = Match.model_validate(record)
    
    # Locate target render job configuration
    target_job: Optional[RenderJob] = None
    for r in match.renders:
        if r.id == render_id:
            target_job = r
            break

    if not target_job:
        logger.error(f"Render failed: RenderJob {render_id} not found in match {match_id}.")
        return

    options = target_job.options
    highlights_only = options.highlights_only
    include_scoreboard = options.include_scoreboard
    include_game_cards = options.include_game_cards
    cpu_mode = options.cpu_mode

    events = match.events
    if not events:
        update_render_job_status(
            match_id, render_id, db_repo,
            status="failed", progress=0, stage="Failed",
            error="No events logged for this match."
        )
        return

    if highlights_only:
        events = [e for e in events if getattr(e, "isHighlight", False)]
        if not events:
            update_render_job_status(
                match_id, render_id, db_repo,
                status="failed", progress=0, stage="Failed",
                error="No highlighted clips found in this match."
            )
            return

    # Check input raw video file
    if not match.video_filename:
        update_render_job_status(
            match_id, render_id, db_repo,
            status="failed", progress=0, stage="Failed",
            error="Match missing raw video upload."
        )
        return

    update_render_job_status(
        match_id, render_id, db_repo,
        status="rendering", progress=5, stage="Preparing source video"
    )

    # Working Directory setup
    local_base = getattr(storage_provider, "base_dir", "storage")
    remote_video_key = f"uploads/{match.video_filename}"
    input_file_path = os.path.join(local_base, remote_video_key)

    # Download from storage if file is not on local server disk
    if not os.path.exists(input_file_path):
        os.makedirs(os.path.dirname(input_file_path), exist_ok=True)
        download_success = storage_provider.download_file(remote_video_key, input_file_path)
        if not download_success or not os.path.exists(input_file_path):
            update_render_job_status(
                match_id, render_id, db_repo,
                status="failed", progress=0, stage="Failed",
                error="Failed to retrieve raw video file from storage."
            )
            return

    temp_dir = os.path.join(local_base, "temp_render_work", f"{match_id}_{render_id}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # 1. Inspect Video Resolution & FPS
        update_render_job_status(
            match_id, render_id, db_repo,
            status="rendering", progress=10, stage="Inspecting video metadata"
        )
        
        orig_width = match.width or 1920
        orig_height = match.height or 1080
        fps_val = match.fps or 30.0
        output_fps = str(round(fps_val, 2))

        # 1080p Max Resolution Normalization
        MAX_WIDTH = 1920
        MAX_HEIGHT = 1080
        if orig_width > MAX_WIDTH or orig_height > MAX_HEIGHT:
            scale_factor = min(MAX_WIDTH / orig_width, MAX_HEIGHT / orig_height)
            width = int(orig_width * scale_factor)
            height = int(orig_height * scale_factor)
            # Ensure dimensions are even numbers for H.264 compatibility
            width = width - (width % 2)
            height = height - (height % 2)
        else:
            width, height = orig_width, orig_height

        # 2. Inspect Color Space & Detect HDR
        color_space, color_trc, color_primaries = "bt709", "bt709", "bt709"
        is_hdr = False
        try:
            cmd_color = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=color_space,color_transfer,color_primaries",
                "-of", "csv=p=0", input_file_path
            ]
            res_color = subprocess.run(cmd_color, capture_output=True, text=True)
            parts = res_color.stdout.strip().rstrip(",").split(",")
            if len(parts) == 3 and parts[0] != "unknown":
                color_space, color_trc, color_primaries = parts
            if "arib-std-b67" in color_trc.lower() or "smpte2084" in color_trc.lower() or "bt2020" in color_space.lower():
                is_hdr = True
        except Exception as e:
            logger.warning(f"Color metadata inspection error: {e}")

        # 3. Encoder Selection (-preset superfast for CPU)
        if cpu_mode:
            encoder = "libx264"
            encoder_opts = ["-preset", "superfast", "-crf", "18"]
        else:
            encoder = "h264_videotoolbox"
            bitrate = "30M"
            encoder_opts = ["-b:v", bitrate]

        # 4. Prepare Scoreboard Generator & Segments
        update_render_job_status(
            match_id, render_id, db_repo,
            status="rendering", progress=15, stage="Generating scoreboard overlays"
        )

        from tt_video_editor import ScoreboardGenerator
        gen = ScoreboardGenerator(match.player1, match.player2, width=width, height=height)

        processed_segments = []
        p1_score, p2_score = 0, 0
        p1_sets, p2_sets = 0, 0
        game_num = 1
        p1_timeout_taken, p2_timeout_taken = False, False

        # Find first winner index for game 1 card
        first_winner_idx = -1
        for idx, e in enumerate(events):
            winner_val = getattr(e, "winner", None)
            if winner_val in [match.player1, match.player2]:
                first_winner_idx = idx
                break

        for i, event in enumerate(events):
            e_winner = getattr(event, "winner", None)
            e_start = getattr(event, "start", 0.0)
            e_end = getattr(event, "end", 0.0)
            e_timeout = getattr(event, "timeout_player", None)

            if not highlights_only and include_game_cards and i == first_winner_idx:
                game_card_path = os.path.join(temp_dir, "game_1.png")
                gen.create_game_card(1, game_card_path)
                processed_segments.append({
                    "type": "card",
                    "path": game_card_path,
                    "duration": 2.0,
                    "filename": "card_game_1.mp4"
                })

            overlay_path = os.path.join(temp_dir, f"score_{i}.png")
            if include_scoreboard:
                gen.create_scoreboard_image(
                    p1_score, p2_score, p1_sets, p2_sets,
                    overlay_path,
                    p1_timeout=p1_timeout_taken,
                    p2_timeout=p2_timeout_taken
                )

            use_overlay = (
                include_scoreboard and 
                (first_winner_idx != -1 and i >= first_winner_idx)
            )

            processed_segments.append({
                "type": "clip",
                "start": e_start,
                "end": e_end,
                "overlay": overlay_path if use_overlay else None,
                "filename": f"clip_event_{i}.mp4"
            })

            # Update scores
            if e_winner == match.player1:
                p1_score += 1
            elif e_winner == match.player2:
                p2_score += 1

            # Game transition
            if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
                if p1_score > p2_score:
                    p1_sets += 1
                else:
                    p2_sets += 1
                p1_score, p2_score = 0, 0
                game_num += 1

                if not highlights_only and include_game_cards and p1_sets < 3 and p2_sets < 3 and i < len(events) - 1:
                    card_path = os.path.join(temp_dir, f"game_{game_num}.png")
                    gen.create_game_card(game_num, card_path)
                    processed_segments.append({
                        "type": "card",
                        "path": card_path,
                        "duration": 2.0,
                        "filename": f"card_game_{game_num}.mp4"
                    })

            if e_timeout:
                if e_timeout == match.player1:
                    p1_timeout_taken = True
                else:
                    p2_timeout_taken = True

        # 5. Render Segments with FFmpeg
        total_segs = len(processed_segments)
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")

        with open(concat_list_path, "w") as f_concat:
            for idx, seg in enumerate(processed_segments):
                # Calculate progress from 20% to 85%
                prog = 20 + int((idx / max(1, total_segs)) * 65)
                update_render_job_status(
                    match_id, render_id, db_repo,
                    status="rendering", progress=prog,
                    stage=f"FFmpeg Encoding (Segment {idx + 1}/{total_segs})"
                )

                seg_output = os.path.join(temp_dir, seg["filename"])
                f_concat.write(f"file '{os.path.abspath(seg_output)}'\n")

                if os.path.exists(seg_output) and os.path.getsize(seg_output) > 0:
                    continue

                if seg["type"] == "card":
                    cmd = [
                        "ffmpeg", "-y", "-loop", "1", "-i", seg["path"],
                        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-t", str(seg["duration"]),
                        "-vf", f"scale={width}:{height}",
                        "-c:v", encoder
                    ] + encoder_opts + [
                        "-color_primaries", color_primaries,
                        "-color_trc", color_trc,
                        "-colorspace", color_space,
                        "-pix_fmt", "yuv420p",
                        "-r", output_fps,
                        "-c:a", "aac", "-b:a", "192k",
                        "-shortest", seg_output
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                elif seg["type"] == "clip":
                    filter_graph = f"scale={width}:{height}[vscaled]"
                    if seg.get("overlay") and os.path.exists(seg["overlay"]):
                        filter_graph = f"[0:v]scale={width}:{height}[vscaled];[vscaled][1:v]overlay=0:0[outv]"
                        map_v = "[outv]"
                        inputs = ["-i", input_file_path, "-i", seg["overlay"]]
                    else:
                        map_v = "[vscaled]"
                        inputs = ["-i", input_file_path]

                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", str(seg["start"]),
                        "-to", str(seg["end"])
                    ] + inputs + [
                        "-filter_complex", filter_graph,
                        "-map", map_v,
                        "-map", "0:a:0?",
                        "-c:v", encoder
                    ] + encoder_opts + [
                        "-color_primaries", color_primaries,
                        "-color_trc", color_trc,
                        "-colorspace", color_space,
                        "-pix_fmt", "yuv420p",
                        "-r", output_fps,
                        "-c:a", "aac", "-b:a", "192k",
                        seg_output
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # 6. Concatenate Segments into Final MP4 Output
        update_render_job_status(
            match_id, render_id, db_repo,
            status="rendering", progress=90, stage="Concatenating final output video"
        )

        output_filename = f"{match_id}_{render_id}.mp4"
        local_output_path = os.path.join(local_base, "renders", output_filename)
        os.makedirs(os.path.dirname(local_output_path), exist_ok=True)

        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            local_output_path
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Upload to remote storage if S3 is active
        remote_render_key = f"renders/{output_filename}"
        if getattr(storage_provider, "bucket_name", None):
            update_render_job_status(
                match_id, render_id, db_repo,
                status="rendering", progress=95, stage="Uploading rendered video to S3"
            )
            storage_provider.upload_file(local_output_path, remote_render_key)

        # 7. Finalize Status
        completed_timestamp = datetime.utcnow().isoformat()
        update_render_job_status(
            match_id, render_id, db_repo,
            status="completed", progress=100, stage="Complete",
            filename=output_filename, completed_at=completed_timestamp
        )
        logger.info(f"Render job {render_id} for match {match_id} completed successfully.")

    except Exception as e:
        logger.error(f"Render execution error for job {render_id}: {e}", exc_info=True)
        update_render_job_status(
            match_id, render_id, db_repo,
            status="failed", progress=0, stage="Failed",
            error=str(e)
        )
    finally:
        # Cleanup temp directory
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass
