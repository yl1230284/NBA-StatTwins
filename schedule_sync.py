"""
Local Background NBA Stats Scheduler (Phase 3)
Allows running recurring automatic updates locally without external dependencies.
Supports both fixed daily schedule (e.g. 04:00 AM) and hourly interval repeating.
"""

import sys
import time
import argparse
import functools
from datetime import datetime, timedelta, timezone
from update_season_stats import update_season, get_sync_metadata

print = functools.partial(print, flush=True)

def run_sync_job(season: str = "2026-27"):
    """Execute the incremental sync and display status."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now_str}] Starting scheduled sync for {season}...")
    try:
        result = update_season(season=season, verbose=True)
        if result.get("success"):
            print(f"[{now_str}] Scheduled sync succeeded: {result.get('records', 0)} players updated.")
        else:
            print(f"[{now_str}] Scheduled sync failed: {result.get('message')}")
    except Exception as e:
        print(f"[{now_str}] Scheduled sync encountered error: {e}")

def schedule_daily(time_str: str = "04:00", season: str = "2026-27"):
    """Schedule daily sync at specified HH:MM local time."""
    try:
        target_hour, target_minute = map(int, time_str.split(":"))
    except ValueError:
        print(f"Error: Invalid time format '{time_str}'. Expected HH:MM (e.g., 04:00)")
        sys.exit(1)

    print("==================================================")
    print("      NBA STATS LOCAL DAILY SCHEDULER             ")
    print(f" Season:      {season}")
    print(f" Scheduled:   Every day at {time_str} (local time)")
    print(" Press Ctrl+C at any time to stop.")
    print("==================================================")

    while True:
        now = datetime.now()
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        # If target time today has already passed, schedule for tomorrow
        if target_time <= now:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        hours_left = wait_seconds / 3600
        print(f"Next sync scheduled in {hours_left:.2f} hours (at {target_time.strftime('%Y-%m-%d %H:%M:%S')}). Sleeping...")

        try:
            time.sleep(wait_seconds)
            run_sync_job(season=season)
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
            break

def schedule_interval(interval_hours: float, season: str = "2026-27"):
    """Repeat sync periodically every interval_hours."""
    print("==================================================")
    print("      NBA STATS LOCAL INTERVAL SCHEDULER          ")
    print(f" Season:      {season}")
    print(f" Interval:    Every {interval_hours} hours")
    print(" Press Ctrl+C at any time to stop.")
    print("==================================================")

    while True:
        wait_seconds = interval_hours * 3600
        print(f"Next sync scheduled in {interval_hours:.1f} hours. Sleeping...")
        try:
            time.sleep(wait_seconds)
            run_sync_job(season=season)
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Background NBA Stats Scheduler")
    parser.add_argument("--season", type=str, default="2026-27", help="NBA Season to update (e.g., 2026-27)")
    parser.add_argument("--daily-at", type=str, default="04:00", help="Daily execution time in HH:MM local format (default: 04:00)")
    parser.add_argument("--interval-hours", type=float, default=None, help="Repeat every N hours instead of fixed daily time")
    parser.add_argument("--run-now", action="store_true", help="Run sync immediately once before entering schedule loop")
    args = parser.parse_args()

    if args.run_now:
        run_sync_job(season=args.season)

    if args.interval_hours is not None:
        schedule_interval(args.interval_hours, season=args.season)
    else:
        schedule_daily(args.daily_at, season=args.season)
