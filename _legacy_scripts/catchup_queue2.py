import os
import subprocess
import time
from datetime import datetime
import sys

# Ensure pytz is installed for accurate UK time on the VPS
try:
    import pytz
except ImportError:
    print("Installing required package 'pytz'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
    import pytz

# The queue uses Linux paths and explicitly calls the local virtual environment Python
QUEUE = [
    {
        "dir": "/root/windows_doors_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": False,
        "run_tj": True
    },
    {
        "dir": "/root/temporary_works_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": False,
        "run_tj": True
    },
    {
        "dir": "/root/firesec_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": False,
        "run_tj": True
    },
    {
        "dir": "/root/estimator_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": False,
        "run_tj": True
    },
    {
        "dir": "/root/height_safety_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": True,
        "run_tj": True
    },
    {
        "dir": "/root/target_waste_management_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": True,
        "run_tj": True
    },
    {
        "dir": "/root/target_electrical_cv_automation",
        "python": "./.venv/bin/python",
        "script": "main.py",
        "run_cv": True,
        "run_tj": True
    }
]

def run_dcm_queue(is_test=False, is_test_10m=False, start_index=0):
    uk_tz = pytz.timezone('Europe/London')
    current_time_str = datetime.now(uk_tz).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n=======================================================")
    if is_test:
        print(f"[{current_time_str}] Starting FAST LIVE TEST DCM Queue (10s wait)...")
    elif is_test_10m:
        print(f"[{current_time_str}] Starting FULL LIVE TEST DCM Queue (10m wait)...")
    else:
        print(f"[{current_time_str}] Starting Nightly VPS DCM Queue...")
    print(f"=======================================================")
    
    queue_to_run = QUEUE[start_index:]
    
    for i, task in enumerate(queue_to_run):
        actual_index = start_index + i
        script_dir = task["dir"]
        python_exe = task["python"]
        script_name = task["script"]
        
        # Portals config (task specific with environment overrides)
        task_run_cv = str(task.get("run_cv", True)).lower()
        task_run_tj = str(task.get("run_tj", True)).lower()
        
        env = os.environ.copy()
        env["CRON_MODE"] = "true"
        env["CDP_PORT"] = "9223"
        env["RUN_CV_LIBRARY"] = task_run_cv
        env["RUN_TOTALJOBS"] = task_run_tj
        
        # Skip completely if both are disabled
        if env["RUN_CV_LIBRARY"] == "false" and env["RUN_TOTALJOBS"] == "false":
            print(f"\n-------------------------------------------------------")
            print(f"Skipping Task {actual_index+1} of {len(QUEUE)}...")
            print(f"Directory: {script_dir}")
            print(f"Reason   : Both portals are disabled.")
            print(f"-------------------------------------------------------")
            continue
        
        if not os.path.exists(script_dir):
            print(f"\n[ERROR] Directory not found on VPS: {script_dir}")
            print("Skipping to next task...")
            continue
            
        print(f"\n-------------------------------------------------------")
        print(f"Executing Task {actual_index+1} of {len(QUEUE)}...")
        print(f"Directory: {script_dir}")
        print(f"Portals  : CV-Library={env['RUN_CV_LIBRARY']} | TotalJobs={env['RUN_TOTALJOBS']}")
        print(f"-------------------------------------------------------")
        
        try:
            cmd = [python_exe, script_name]
            process = subprocess.run(
                cmd, 
                cwd=script_dir, 
                env=env,
                timeout=14400  # 4 hour maximum time limit to prevent permanent hangs
            )
            
            if process.returncode != 0:
                print(f"[WARNING] Task finished with a non-zero exit code: {process.returncode}")
            else:
                print(f"[SUCCESS] Task {actual_index+1} finished successfully.")
                
        except subprocess.TimeoutExpired:
            print(f"[ERROR] Task {actual_index+1} exceeded the maximum time limit (4 hours) and was forcefully terminated to save the queue.")
        except Exception as e:
            print(f"[ERROR] Failed to execute task: {e}")
            
        if i < len(QUEUE) - 1:
            sleep_time = 10 if (is_test and not is_test_10m) else 120
            print(f"\n[{datetime.now(uk_tz).strftime('%Y-%m-%d %H:%M:%S')}] Waiting {sleep_time} seconds to cool down...")
            time.sleep(sleep_time)
            
    print(f"\n[{datetime.now(uk_tz).strftime('%Y-%m-%d %H:%M:%S')}] All DCM Automations completed for the day!")
    print("Going back to sleep until tomorrow at 02:00 AM UK time...\n")

def main():
    print("VPS Master Scheduler Initialized in Background.")
    print("Waiting for exactly 02:00 AM (UK Time) to trigger the sequence...")
    
    last_run_day = None
    uk_tz = pytz.timezone('Europe/London')
    
    while True:
        now = datetime.now(uk_tz)
        if now.hour == 1 and now.minute == 0:
            if last_run_day != now.day:
                last_run_day = now.day
                run_dcm_queue()
                
        time.sleep(30)

if __name__ == "__main__":
    run_dcm_queue(is_test=False, is_test_10m=False, start_index=1)
