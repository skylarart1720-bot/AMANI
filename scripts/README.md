# Local commands

From the project directory:

```powershell
# Build both browser applications
npm.cmd run build

# Start production builds and API services quietly
.\.venv\Scripts\python.exe scripts\run_local.py

# Or run development frontends
.\.venv\Scripts\python.exe scripts\run_local.py --dev

# Stop only processes identified as belonging to this launcher
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\stop-local.ps1

# Check external providers without printing credentials
.\.venv\Scripts\python.exe scripts\check_integrations.py

# Exercise the running website and moderator flow
.\.venv\Scripts\python.exe scripts\browser_check.py
```

The launcher uses free ports and prints the actual URLs. Defaults are website 3000, moderators 3100, API 8100, scanner 8200 and WhatsApp 8300. `.runtime/services.json` records the selected ports. Logs are in `.runtime/`. It does not terminate unrelated Next.js or Python processes.

Moderator login: use `ADMIN_API_TOKEN` from your environment or the generated local token in `data/.admin-token`. Do not share that token publicly.
