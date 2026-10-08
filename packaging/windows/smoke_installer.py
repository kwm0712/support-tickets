"""Install/run/restart/uninstall the built EXE on a disposable Windows CI runner.
This is package smoke evidence only, not production or business acceptance.
"""
from __future__ import annotations
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "release" / "windows" / "smoke-evidence"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = {
    "scope": "Windows installation, rendered login, application restart, uninstall",
    "production_acceptance": False,
    "not_tested": ["business transaction / target PostgreSQL", "SSO/IAP", "live embeddings", "target backup/restore", "OS reboot", "standard-user UAC boundary"],
    "commit": os.getenv("GITHUB_SHA"),
    "run_id": os.getenv("GITHUB_RUN_ID"),
    "os": platform.platform(),
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "checks": [],
}
WORK = Path(tempfile.mkdtemp(prefix="Compelec Windows Smoke "))
INSTALL = WORK / "Installed Application"
DATA = WORK / "Application Data"

def record(name, **details):
    REPORT["checks"].append({"name": name, "status": "passed", **details})

def stop(process):
    if process and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        process.wait(timeout=30)

def run_ui(exe, attempt):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["CCS_DATA_DIR"] = str(DATA)
    env["CCS_LICENSE_MODE"] = "demo"
    env["STREAMLIT_SERVER_PORT"] = "18501"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    port = 18501
    url = f"http://127.0.0.1:{port}"
    process = None
    with (OUT / f"start-{attempt}.stdout.log").open("w") as stdout, (OUT / f"start-{attempt}.stderr.log").open("w") as stderr:
        try:
            process = subprocess.Popen([str(exe)], cwd=WORK, env=env, stdout=stdout, stderr=stderr)
            deadline = time.monotonic() + 90
            ready = False
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Installed EXE exited: {process.returncode}; see start-{attempt}.stderr.log")
                try:
                    with urllib.request.urlopen(url + "/_stcore/health", timeout=2) as response:
                        ready = response.status == 200 and response.read().decode().strip() == "ok"
                    if ready:
                        break
                except Exception:
                    pass
                time.sleep(1)
            if not ready:
                raise RuntimeError("Installed app health timeout")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.get_by_role("button", name="Anmelden", exact=True).wait_for(timeout=45000)
                    page.get_by_label("Benutzername", exact=True).wait_for()
                    page.get_by_label("Kennwort", exact=True).wait_for()
                    if page.locator('[data-testid="stException"]').count():
                        raise RuntimeError("Rendered Streamlit exception")
                    page.screenshot(path=str(OUT / f"login-{attempt}.png"), full_page=True)
                    record(f"installed_login_render_{attempt}", health="ok", data_dir_exists=DATA.exists())
                except Exception:
                    page.screenshot(path=str(OUT / f"failure-{attempt}.png"), full_page=True)
                    (OUT / f"page-{attempt}.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
                    raise
                finally:
                    browser.close()
        finally:
            stop(process)

failed = False
try:
    if sys.platform != "win32":
        raise RuntimeError("This test requires Windows")
    setups = list((ROOT / "release" / "windows").glob("COMPELEC-ONE-Business-Setup-*.exe"))
    if len(setups) != 1:
        raise RuntimeError(f"Expected one installer, found {len(setups)}")
    setup = setups[0]
    REPORT["installer"] = setup.name
    REPORT["sha256"] = hashlib.sha256(setup.read_bytes()).hexdigest()
    signature = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-AuthenticodeSignature -LiteralPath $env:SMOKE_SETUP | Select-Object Status,StatusMessage | ConvertTo-Json -Compress"],
        env={**os.environ, "SMOKE_SETUP": str(setup)}, text=True, capture_output=True, check=True,
    )
    REPORT["authenticode"] = json.loads(signature.stdout)
    # Unsigned is recorded explicitly; this build does not claim signing approval.
    result = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", f"/DIR={INSTALL}", f"/LOG={OUT / 'install.log'}"], timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"Installation returned {result.returncode}")
    exe = INSTALL / "COMPELEC-ONE-Business.exe"
    if not exe.is_file():
        raise RuntimeError("Installed executable missing")
    record("installation", exit_code=result.returncode)
    run_ui(exe, 1)
    run_ui(exe, 2)
except Exception as exc:
    failed = True
    REPORT["error"] = str(exc)
finally:
    uninstaller = INSTALL / "unins000.exe"
    if uninstaller.exists():
        try:
            result = subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LOG={OUT / 'uninstall.log'}"], timeout=180)
            for _ in range(30):
                if not (INSTALL / "COMPELEC-ONE-Business.exe").exists():
                    break
                time.sleep(1)
            if result.returncode != 0 or (INSTALL / "COMPELEC-ONE-Business.exe").exists():
                raise RuntimeError(f"Uninstall failed: exit {result.returncode}")
            record("uninstallation", exit_code=result.returncode)
        except Exception as exc:
            failed = True
            REPORT["uninstall_error"] = str(exc)
    REPORT["status"] = "failed" if failed else "passed"
    REPORT["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (OUT / "smoke-result.json").write_text(json.dumps(REPORT, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
    if not failed:
        shutil.rmtree(WORK, ignore_errors=True)
sys.exit(1 if failed else 0)
