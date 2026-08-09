#!/usr/bin/env python3
import os
import sys
import logging

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gpu_worker")

def main():
    match_id = os.getenv("MATCH_ID")
    render_id = os.getenv("RENDER_ID")

    if not match_id or not render_id:
        logger.error("Missing required environment variables: MATCH_ID and RENDER_ID must be set.")
        sys.exit(1)

    logger.info(f"🚀 Starting AWS Batch GPU render job for Match: {match_id}, Render: {render_id}")

    from app.database import get_db
    from app.storage import get_storage_provider
    from app.render_adapter import execute_render_job

    db = get_db()
    storage = get_storage_provider()

    try:
        execute_render_job(match_id=match_id, render_id=render_id, db_repo=db, storage_provider=storage)
        logger.info(f"✅ AWS Batch GPU render job completed successfully for Render: {render_id}")
    except Exception as e:
        logger.error(f"❌ AWS Batch GPU render job failed for Render {render_id}: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
