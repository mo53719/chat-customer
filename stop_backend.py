import subprocess, time
r = subprocess.run(["powershell", "-Command",
    "$p = (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess; if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }"],
    capture_output=True, text=True)
time.sleep(2)
print("Backend stopped:", r.stdout or "OK")
