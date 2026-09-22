#!/usr/bin/env python3
"""
AWS Batch GPU Worker entrypoint for AI Rally Detection.
"""

import os
import sys
import logging

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gpu_detect_worker")


def main():
    match_id = os.getenv("MATCH_ID")
    job_id = os.getenv("JOB_ID")

    if not match_id or not job_id:
        logger.error("Missing required environment variables: MATCH_ID and JOB_ID must be set.")
        sys.exit(1)

    logger.info(f"🚀 Starting AWS Batch GPU AI detect job for Match: {match_id}, Job: {job_id}")

    from app.database import get_db_repository
    from app.storage import get_storage_provider
    from app.detect_adapter import execute_auto_detect_job

    db = get_db_repository()
    storage = get_storage_provider()
    mode = os.getenv("DETECT_MODE", "replace")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    try:
        execute_auto_detect_job(
            match_id=match_id,
            job_id=job_id,
            db_repo=db,
            storage_provider=storage,
            mode=mode,
            model=model
        )
        logger.info(f"✅ AWS Batch GPU AI detect job completed successfully for Job: {job_id}")
    except Exception as e:
        logger.error(f"❌ AWS Batch GPU AI detect job failed for Job {job_id}: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
