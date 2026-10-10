"""Start production builds on free loopback ports without opening console windows."""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
RUNTIME.mkdir(exist_ok=True)
MANIFEST = RUNTIME / "services.json"

def free_port(start):
    for port in range(start, start + 100):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found")

def reachable(url):
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    if MANIFEST.exists():
        existing = json.loads(MANIFEST.read_text())
        if all(reachable(item["health"]) for item in existing):
            for item in existing:
                print(f"{item['name']}: {item['url']}")
            return
    load_dotenv(ROOT / ".env")
    env = os.environ.copy()
    env["DATABASE_URL"] = ""
    env["APP_ENV"] = "local"
    env["AMANI_DATA_DIR"] = str(ROOT / "data")
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    ports = {"api": free_port(8100), "scanner": free_port(8200), "web": free_port(3000), "moderator": free_port(3100), "whatsapp": free_port(8300)}
    env["ORCHESTRATOR_URL"] = f"http://127.0.0.1:{ports['api']}"
    env["URL_SAFETY_URL"] = f"http://127.0.0.1:{ports['scanner']}"
    env["WHATSAPP_GATEWAY_URL"] = f"http://127.0.0.1:{ports['whatsapp']}"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required")
    definitions = [("api", "apps/orchestrator"), ("scanner", "services/url-safety"), ("whatsapp", "apps/whatsapp-gateway"), ("web", "apps/web"), ("moderator", "apps/moderator-dashboard")]
    processes = []
    manifest = []
    try:
        for name, directory in definitions:
            folder = ROOT / directory
            if name in ("web", "moderator"):
                if not args.dev and not (folder / ".next/BUILD_ID").exists():
                    raise RuntimeError(f"Build {directory} before starting: npm.cmd --prefix {directory} run build")
                command = [node, str(folder / "node_modules/next/dist/bin/next"), "dev" if args.dev else "start", "-H", "127.0.0.1", "-p", str(ports[name])]
            else:
                command = [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(ports[name]), "--no-access-log"]
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            with (RUNTIME / f"{name}.log").open("ab") as output:
                process = subprocess.Popen(command, cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=output, creationflags=flags, start_new_session=os.name != "nt")
            processes.append(process)
            url = f"http://127.0.0.1:{ports[name]}"
            manifest.append({"name": name, "pid": process.pid, "url": url, "health": url + ("/health" if name not in ("web", "moderator") else ""), "command": command})
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A service exited. Check .runtime/*.log")
            if all(reachable(item["health"]) for item in manifest):
                MANIFEST.write_text(json.dumps(manifest, indent=2))
                for item in manifest:
                    print(f"{item['name']}: {item['url']}")
                print("Choose Super Admin and use data/.admin-token (unless ADMIN_API_TOKEN is configured). Create staff IDs/passwords in Staff accounts.")
                return
            time.sleep(1)
        raise RuntimeError("Services did not become ready in time. Check .runtime/*.log")
    except Exception:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        raise

if __name__ == "__main__":
    main()
