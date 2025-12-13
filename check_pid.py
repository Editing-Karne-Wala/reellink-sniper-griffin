import psutil
import sys
import os

pid = int(sys.argv[1])
pid_file = "bot.pid"

if psutil.pid_exists(pid):
    try:
        proc = psutil.Process(pid)
        if 'python' in proc.name().lower():
            print(f"Process {pid} is a Python process and is running.")
            sys.exit(0) # Process exists and is Python
        else:
            print(f"Process {pid} exists but is not a Python process.")
            sys.exit(1) # Process exists but not Python
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        print(f"Process {pid} does not exist or access denied.")
        sys.exit(1) # Process does not exist or access denied
else:
    print(f"Process {pid} does not exist.")
    sys.exit(1) # Process does not exist

if os.path.exists(pid_file):
    os.remove(pid_file)
    print(f"Removed stale PID file: {pid_file}")
