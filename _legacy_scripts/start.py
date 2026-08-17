import os
import subprocess

cmd = """ssh root@139.59.191.27 "pkill -f queue2_scheduler; pkill -f height_safety; rm -f /root/height_safety_cv_automation/automation.lock /root/target_electrical_cv_automation/automation.lock; nohup python3 /root/queue2_scheduler.py --run-now --start-from 9 > /root/queue2_scheduler.log 2>&1 </dev/null &" """

subprocess.run(cmd, shell=True)
