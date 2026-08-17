import os
with open("/root/queue1_scheduler.py", "r") as f:
    text = f.read()

# Fix the broken line
text = text.replace('env[" CDP_PORT\\] = \\9222', 'env["CDP_PORT"] = "9222"')
text = text.replace('env[" CDP_PORT\\\\] = \\\\9222', 'env["CDP_PORT"] = "9222"')
text = text.replace('env[" CDP_PORT"] = "9222"', 'env["CDP_PORT"] = "9222"')

with open("/root/queue1_scheduler.py", "w") as f:
    f.write(text)
