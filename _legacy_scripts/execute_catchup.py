import subprocess

cmd = """ssh root@139.59.191.27 "pkill -f queue2_scheduler.py; pgrep -f 'python3 main.py' | xargs -r kill -9; pgrep -f chrome | xargs -r kill -9; rm -f /root/*_cv_automation/automation.lock; rm -f /home/talentverse/.config/chromium-profile-2/SingletonLock; nohup python3 /root/catchup_queue2.py > /root/queue2_logs.txt 2>&1 &" """
subprocess.run(cmd, shell=True)
