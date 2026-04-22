from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import SyncTrigger
from app.services.backup import create_encrypted_backup
from app.services.canvas.sync import run_canvas_sync

scheduler = BackgroundScheduler(timezone=get_settings().default_timezone)


def _daily_canvas_sync_job() -> None:
    db = SessionLocal()
    try:
        run_canvas_sync(db, trigger_type=SyncTrigger.scheduled, snapshot_label="Daily scheduled sync")
    finally:
        db.close()


def _daily_backup_job() -> None:
    db = SessionLocal()
    try:
        create_encrypted_backup(db, note="Daily scheduled backup")
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return

    scheduler.add_job(
        _daily_canvas_sync_job,
        trigger=CronTrigger.from_crontab(settings.daily_sync_cron),
        id="daily-canvas-sync",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        _daily_backup_job,
        trigger=CronTrigger.from_crontab(settings.daily_backup_cron),
        id="daily-backup",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
