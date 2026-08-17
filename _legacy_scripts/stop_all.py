import os
import subprocess

cmd = """ssh root@139.59.191.27 "pkill -f queue1_scheduler; pkill -f queue2_scheduler; ps -ef | grep 'python' | grep -E 'main\.py' | grep -v grep | awk '{print \\$2}' | xargs -r kill -9; rm -f /root/*_cv_automation/automation.lock" """
subprocess.run(cmd, shell=True)
