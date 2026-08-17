import os
import subprocess

cmd = """ssh root@139.59.191.27 "killall -9 chrome chromium; rm -f /home/talentverse/snap/chromium/common/chromium/SingletonLock /home/talentverse/.config/chromium-profile-2/SingletonLock /home/talentverse/.config/google-chrome/SingletonLock" """
subprocess.run(cmd, shell=True)
