import os
import subprocess

cmd = """ssh root@139.59.191.27 "ps -ef | grep chrome | awk '{print \\$2}' | xargs -r kill -9; rm -f /home/talentverse/snap/chromium/common/chromium/SingletonLock /home/talentverse/.config/chromium-profile-2/SingletonLock" """
subprocess.run(cmd, shell=True)
