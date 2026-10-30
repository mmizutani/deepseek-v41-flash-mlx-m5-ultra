"""The server: started in the background (pid file, log) or in the foreground (the launchd unit), stopped, watched."""

import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

from .config import Settings


def weights_gib(s: Settings) -> float:
    """The checkpoint's resident share once loaded: its safetensors shards (the engram tables stay on disk)."""
    return sum(f.stat().st_size for f in s.model.glob("*.safetensors")) / 2**30


def health(s: Settings, timeout: float = 3) -> dict | None:
    try:
        with urllib.request.urlopen(s.url.removesuffix("/v1") + "/health", timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def identity(number: int) -> dict | None:
    """A PID alone is reusable; compare its executable and start time before signalling."""
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        return None
    result = subprocess.run(["ps", "-ww", "-p", str(number), "-o", "lstart=", "-o", "comm="],
                            capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
    parts = result.stdout.strip().split(maxsplit=5)
    if result.returncode or len(parts) != 6:
        return None
    return {"pid": number, "started": " ".join(parts[:5]), "executable": str(Path(parts[5]).resolve())}


def record(s: Settings) -> dict | None:
    try:
        saved = json.loads(s.pid_file.read_text())
        if isinstance(saved, dict) and saved.get("executable") == str(s.run_binary.resolve()):
            return saved
    except (OSError, ValueError):
        pass
    return None


def pid(s: Settings) -> int | None:
    saved = record(s)
    if saved and saved == identity(saved.get("pid")):
        return saved["pid"]
    return None


def clear_record(s: Settings, saved: dict) -> None:
    if record(s) == saved:
        s.pid_file.unlink(missing_ok=True)


def free_gib() -> float:
    """Memory a load can take: RAM less wired, compressed and anonymous pages (the file cache gives way)."""
    out = subprocess.run(["vm_stat"], capture_output=True, text=True, check=True).stdout
    size = int(out.split("page size of ")[1].split()[0])
    pages = {line.split(":")[0]: int(line.split(":")[1].strip().rstrip(".")) for line in out.splitlines()[1:] if ":" in line}
    held = sum(pages.get(k, 0) for k in ("Pages wired down", "Pages occupied by compressor", "Anonymous pages"))
    ram = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True).stdout)
    return (ram - held * size) / 2**30


def memory_check(s: Settings) -> None:
    need = weights_gib(s) + s.memory_margin_gib + max(s.prompt_cache_gib, 0)
    have = free_gib()
    if have < need:
        raise SystemExit(f"{have:.0f} GiB free, the server needs {need:.0f}: stop other models (8888's?) first")


def wait_ready(s: Settings, proc: subprocess.Popen, limit: float = 900) -> None:
    t0 = time.time()
    while time.time() - t0 < limit:
        if health(s):
            return
        if proc.poll() is not None:
            raise SystemExit(f"the server exited while loading; see {s.log_file}")
        time.sleep(3)
    raise SystemExit(f"not ready after {limit:.0f} s; see {s.log_file}")


def up(s: Settings, foreground: bool = False) -> None:
    if pid(s) or health(s):
        raise SystemExit(f"already serving at {s.url}")
    memory_check(s)
    args = s.serve_args()
    if foreground:  # the launchd unit: this process becomes the server
        os.execve(args[0], args, s.server_env())
    s.cache.mkdir(parents=True, exist_ok=True)
    with open(s.log_file, "ab") as log:
        p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=s.server_env(), start_new_session=True)
    saved = identity(p.pid)
    if not saved or saved["executable"] != str(s.run_binary.resolve()):
        p.terminate()
        p.wait()
        raise SystemExit(f"could not verify the started server; see {s.log_file}")
    try:
        s.pid_file.write_text(json.dumps(saved) + "\n")
    except OSError:
        p.terminate()
        p.wait()
        raise
    try:
        wait_ready(s, p)
    except BaseException:
        # Keep a live timed-out child's identity so down can still stop it safely.
        if p.poll() is not None:
            clear_record(s, saved)
        raise
    print(f"serving {s.served_name} at {s.url} (pid {p.pid})")


def down(s: Settings, grace: float = 30) -> None:
    saved = record(s)
    if not saved or saved != identity(saved.get("pid")):
        print("not running with a verified identity; no signal sent")
        return
    p = saved["pid"]
    try:
        os.kill(p, signal.SIGTERM)
    except ProcessLookupError:
        clear_record(s, saved)
        return
    t0 = time.time()
    while time.time() - t0 < grace:
        if identity(p) != saved:
            break
        time.sleep(0.5)
    else:
        if identity(p) == saved:
            try:
                os.kill(p, signal.SIGKILL)
            except ProcessLookupError:
                pass
    clear_record(s, saved)
    print("stopped")


def status(s: Settings) -> str:
    h = health(s)
    return f"pid: {pid(s) or 'not running'}\nurl: {s.url}\nhealth: {json.dumps(h) if h else 'down'}"


def chat(s: Settings, prompt: str, max_tokens: int = 128) -> str:
    body = {"model": s.served_name, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(s.url + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]
