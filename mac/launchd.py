"""The launchd unit: `up --foreground` at login, kept alive, serving the LAN on a port. Written with this Mac's paths
(nothing machine-specific is committed); loading it is left to the user:
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tensorfold.deepseek-v41.plist"""

import shutil
import os
import tempfile
from dataclasses import fields
from pathlib import Path
from xml.sax.saxutils import escape

from .config import ROOT, Settings

LABEL = "com.tensorfold.deepseek-v41"


def plist(s: Settings, port: int) -> str:
    python = shutil.which("python3") or "/usr/bin/python3"
    env = {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"}
    # launchd does not inherit this shell. Preserve explicitly supplied recipe overrides only.
    for field in fields(s):
        name = field.name.upper()
        if name in os.environ:
            value = getattr(s, field.name)
            env[name] = str(value).lower() if isinstance(value, bool) else str(value)
    if s.api_key:
        env["API_KEY"] = s.api_key
    if os.environ.get("TENSORFOLD_API_KEY"):
        env["TENSORFOLD_API_KEY"] = os.environ["TENSORFOLD_API_KEY"]
    env.update(PORT=str(port), HOST="0.0.0.0")
    env_xml = "".join(f"<key>{k}</key><string>{escape(v)}</string>" for k, v in env.items())
    log = escape(str(s.cache / "launchd.log"))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>{escape(python)}</string><string>-m</string><string>mac</string><string>up</string><string>--foreground</string></array>
  <key>WorkingDirectory</key><string>{escape(str(ROOT))}</string>
  <key>EnvironmentVariables</key><dict>{env_xml}</dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""


def write(s: Settings, port: int) -> str:
    path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    path.parent.mkdir(parents=True, exist_ok=True)
    s.cache.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(plist(s, port))
            f.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    warning = "warning: this unit serves the LAN without an API key\n" if not (s.api_key or os.environ.get("TENSORFOLD_API_KEY")) else ""
    return warning + f"wrote {path} (not loaded): launchctl bootstrap gui/$(id -u) {path}"
