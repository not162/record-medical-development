"""
Worker mandiri untuk Docker/Render: polling antrian TrainingJob dan menjalankan training.
Jalankan dari direktori services/ai-api:  python worker.py
"""
import logging
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.ml.training_worker import process_next_job  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")

POLL_INTERVAL = float(os.getenv("WORKER_POLL_INTERVAL", "5"))
_stop = False


def _handle_signal(signum, frame):
    global _stop
    logger.info("Sinyal %s diterima, berhenti setelah job saat ini selesai...", signum)
    _stop = True


def main() -> int:
    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    Base.metadata.create_all(bind=engine)
    logger.info("Worker aktif, polling tiap %.1f detik.", POLL_INTERVAL)
    while not _stop:
        try:
            result = process_next_job()
        except Exception as e:
            logger.error("Error loop worker: %s", e, exc_info=True)
            result = None
        if result is None:
            # Tidur dalam potongan kecil agar SIGINT responsif
            waited = 0.0
            while waited < POLL_INTERVAL and not _stop:
                time.sleep(0.25)
                waited += 0.25
        else:
            logger.info("Job %s selesai dengan status %s", result["job_id"], result["status"])
    logger.info("Worker berhenti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
