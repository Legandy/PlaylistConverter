import threading, time
from conversion import initial_sync_with_comparison, log

# Starts a background thread that triggers sync at a fixed schedule
def start_scheduler(cfg, dry_run=False, verbose=False, dev_mode=False, interval="30min"):
    def scheduler_loop():
        interval_sec = parse_interval(interval)
        if interval_sec is None:
            log(f"⛔ Invalid schedule interval: {interval}")
            return

        log(f"🕒 Scheduled sync started — every {interval}")
        while True:
            try:
                initial_sync_with_comparison(cfg, dry_run=dry_run, verbose=verbose, dev_mode=dev_mode)
                log(f"✅ Sync complete (scheduled interval: {interval})")
                time.sleep(interval_sec)
            except Exception as e:
                log(f"🚨 Scheduler error — {e}")
                time.sleep(30)  # brief pause before retrying

    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()

# Parses human-readable interval string into seconds
def parse_interval(interval_str):
    interval_str = interval_str.strip().lower()

    if interval_str == "never":
        return None
    if "15" in interval_str:
        return 15 * 60
    if "30" in interval_str:
        return 30 * 60
    if "hour" in interval_str:
        return 60 * 60
    if "daily" in interval_str and "@02:00" in interval_str:
        now = time.localtime()
        now_sec = time.mktime(now)
        target = time.strptime(f"{now.tm_year}-{now.tm_mon}-{now.tm_mday} 02:00:00", "%Y-%m-%d %H:%M:%S")
        target_sec = time.mktime(target)
        delay = (target_sec - now_sec) % (24 * 3600)
        return delay if delay > 0 else 3600 * 24
    return None