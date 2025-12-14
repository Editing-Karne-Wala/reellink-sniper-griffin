import logging
import sys
import atexit
import psutil  # Use the more reliable psutil library
from apscheduler.schedulers.background import BackgroundScheduler
from src.refresh_cookies import refresh_session  # Import your script

# Add this line to silence the noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)

PID_FILE = "bot.pid"


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule the refresh to run every 24 hours
    scheduler.add_job(func=refresh_session, trigger="interval", hours=24)
    scheduler.start()
    print("Internal Scheduler Started: Cookies will refresh every 24h.")

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


def is_process_running(pid: int) -> bool:
    """
    Check if a process with the given PID is running and is a Python process.
    Uses psutil for cross-platform reliability.
    """
    if not psutil.pid_exists(pid):
        return False
    try:
        proc = psutil.Process(pid)
        # Check if it's a python process, adjust 'python.exe' for other OS if needed
        return 'python' in proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        # PID existed but now it doesn't, or we don't have permission
        return False
    except Exception as e:
        logging.error(f"Error checking process with psutil: {e}")
        return False


def cleanup_pid_file():
    """Ensure the PID file is removed on exit."""
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
            logging.info("PID file cleaned up.")
        except OSError as e:
            logging.error(f"Error removing PID file on cleanup: {e}")


def main_with_pid_check():
    """
    Checks for an existing bot process using a PID file before starting.
    Now uses a more robust psutil check.
    """

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())

            if is_process_running(pid):
                logging.warning(f"Bot process with PID {pid} is already running. Exiting.")
                sys.exit(0)
            else:
                logging.info("Found stale PID file for a non-running process. Removing it.")
                # No need to call cleanup_pid_file, just remove it directly
                os.remove(PID_FILE)

        except (ValueError, FileNotFoundError) as e:
            logging.warning(f"Could not read PID file or PID was invalid: {e}. Assuming bot is not running.")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)  # Clean up the invalid file

    # Register cleanup to run on normal script exit
    atexit.register(cleanup_pid_file)

    # Write the new PID file for the current process
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
            logging.info(f"Wrote new PID file for process {os.getpid()}.")
    except IOError as e:
        logging.error(f"Failed to write PID file: {e}")
        sys.exit(1)
        
    # 1. Run it once immediately so we have fresh cookies NOW
    print("Performing initial cookie refresh...")
    if not refresh_session():
        print("Initial Instagram cookie refresh failed. Continuing with existing cookies (if any).")

    # 2. Start the timer for the future
    start_scheduler()

    # 3. Start your Bot
    from src.bot import main
    try:
        main()
    finally:
        # This will be called on Ctrl+C or normal exit of main()
        cleanup_pid_file()


if __name__ == "__main__":
    main_with_pid_check()