"""The engine: a worktree of the TensorFold checkout at the pinned commit, built under tf_cache (never in the
checkout), libjpeg-turbo 3.1.4.1 built from its release beside it (the engine's JPEG decoder pins that release), and
libtfgrammar (structured output) from xgrammar at the tag the engine pins."""

import shutil
import hashlib
import ssl
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .config import JPEG_VERSION, Settings

# xgrammar's release the engine's structured output is built against (zig/build/grammar.zig pins the tag), and its commit
XGRAMMAR_TAG = "v0.2.8"
XGRAMMAR_COMMIT = "97787376faee5ed8466cfad57c99855e4ce2f6aa"
XGRAMMAR_REPO = "https://github.com/mlc-ai/xgrammar"

# Published SHA-256 for the source asset in libjpeg-turbo's 3.1.4.1 GitHub release.
JPEG_SHA256 = "ecae8008e2cc9ade2f2c1bb9d5e6d4fb73e7c433866a056bd82980741571a022"
JPEG_URL = f"https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/{JPEG_VERSION}/libjpeg-turbo-{JPEG_VERSION}.tar.gz"


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def zig_executable(s: Settings) -> str:
    executable = shutil.which(str(s.path(s.zig))) if s.zig else None
    if not executable:
        raise SystemExit(f"Zig executable not found: {s.zig!r}. Install Zig 0.17.0 on PATH, "
                         "or set [engine] zig in local.toml (or ZIG) to its executable path.")
    return executable


def build_engine(s: Settings, rebuild: bool = False) -> Path:
    if s.binary:
        return s.run_binary
    if not s.tensorfold_sha:
        raise SystemExit("no tensorfold_sha pinned (local.toml)")
    src = s.path(s.tensorfold_src)
    if not s.worktree.exists():
        s.worktree.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "-C", str(src), "worktree", "add", "--detach", str(s.worktree), s.tensorfold_sha])
    if rebuild or not s.built_binary.exists():
        _run([zig_executable(s), "build", "native", "-Doptimize=ReleaseFast", f"-Dcpu={s.zig_cpu}"], cwd=s.worktree, env=s.build_env())
    return s.built_binary


def jpeg_archive(work: Path) -> Path:
    tgz = work / f"libjpeg-turbo-{JPEG_VERSION}.tar.gz"
    if tgz.exists():
        with tgz.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if digest != JPEG_SHA256:
            raise SystemExit(f"SHA-256 mismatch for cached {tgz}; remove this archive and retry")
        return tgz
    print("downloading", JPEG_URL, flush=True)
    ctx = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    with tempfile.NamedTemporaryFile(dir=work, prefix="jpeg-", suffix=".part", delete=False) as f:
        temporary = Path(f.name)
        try:
            with urllib.request.urlopen(JPEG_URL, context=ctx, timeout=60) as r:
                shutil.copyfileobj(r, f)
            f.close()
            with temporary.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != JPEG_SHA256:
                raise SystemExit(f"SHA-256 mismatch downloading {JPEG_URL}; archive was not cached or extracted")
            temporary.replace(tgz)
        finally:
            temporary.unlink(missing_ok=True)
    return tgz


def build_jpeg(s: Settings) -> Path:
    if s.jpeg_lib.exists():
        return s.jpeg_lib
    work = s.cache / "jpeg-src"
    work.mkdir(parents=True, exist_ok=True)
    tgz = jpeg_archive(work)
    with tarfile.open(tgz) as t:
        t.extractall(work, filter="data")
    srcdir = work / f"libjpeg-turbo-{JPEG_VERSION}"
    build = work / "build"
    prefix = s.jpeg_lib.parent.parent
    _run(["cmake", "-S", str(srcdir), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={prefix}"])
    _run(["cmake", "--build", str(build), "-j", "8"])
    _run(["cmake", "--install", str(build)])
    return s.jpeg_lib


def build_grammar(s: Settings, rebuild: bool = False) -> Path:
    """libtfgrammar beside the binary (the server loads it at the first structured request): xgrammar cloned once into
    tf_cache with its submodules, then zig build grammar in the worktree."""
    if s.binary or (s.built_grammar.exists() and not rebuild):
        return s.built_grammar
    root = s.cache / f"xgrammar-{XGRAMMAR_TAG}"
    if not (root / ".git").exists():
        _run(["git", "clone", "--branch", XGRAMMAR_TAG, "--recurse-submodules", XGRAMMAR_REPO, str(root)])
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    if head != XGRAMMAR_COMMIT:
        raise SystemExit(f"{root} is at {head[:8]}, not xgrammar {XGRAMMAR_TAG}'s {XGRAMMAR_COMMIT[:8]}; remove it to clone again")
    _run([zig_executable(s), "build", "grammar", f"-Dxgrammar={root}", f"-Dcpu={s.zig_cpu}"], cwd=s.worktree, env=s.build_env())
    if not s.built_grammar.exists():
        raise SystemExit(f"the build left no {s.built_grammar}")
    return s.built_grammar


def build(s: Settings, rebuild: bool = False) -> None:
    build_engine(s, rebuild)
    build_grammar(s, rebuild)
    if s.vision:
        build_jpeg(s)
