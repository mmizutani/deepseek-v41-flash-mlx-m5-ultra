"""Register this recipe's OpenAI-compatible endpoint with Pi coding agent."""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from .config import Settings

PROVIDER = "local-deepseek"


def provider(s: Settings) -> dict:
    # Pi interpolates $ and executes a leading ! in apiKey. Escape a literal server key.
    key = (s.api_key or "local").replace("$", "$$")
    if key.startswith("!"):
        key = "$!" + key[1:]
    model = {
        "id": s.served_name,
        "name": f"{s.served_name} (Local)",
        "reasoning": True,
        "thinkingLevelMap": {"minimal": "minimal", "low": "low", "medium": "medium",
                             "high": "high", "xhigh": None, "max": "max"},
        "input": ["text", "image"] if s.vision else ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "contextWindow": s.context,
        "maxTokens": s.max_tokens,
        "compat": {
            "maxTokensField": "max_tokens",
            "supportsStore": False,
            "supportsDeveloperRole": False,
            "supportsReasoningEffort": True,
            # TensorFold accepts enable_thinking and reasoning_effort at the top level.
            # Pi calls that wire format "qwen" regardless of the served model family.
            "thinkingFormat": "qwen",
        },
    }
    if s.vision:
        model["inputLimits"] = {"images": {"maxPerMessage": s.vision_max_images,
                                          "maxPerRequest": s.vision_max_images}}
    return {"name": "Local DeepSeek (TensorFold)", "baseUrl": s.url,
            "api": "openai-completions", "apiKey": key, "models": [model]}


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
    except ValueError as e:
        raise ValueError(f"{path}: invalid JSON: {e}") from e
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _write(path: Path, value: dict) -> None:
    # Stage beside the destination, then replace it so readers never see partial JSON.
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=f".{path.name}-", delete=False) as f:
        temporary = Path(f.name)  # NamedTemporaryFile creates mode 0600, including for API keys.
        try:
            f.write(json.dumps(value, indent=2) + "\n")
            f.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def setup(s: Settings, agent_dir: Path | None = None, make_default: bool = True) -> list[str]:
    """Merge the local provider, back up changed files, and optionally select it by default."""
    directory = Path(agent_dir or os.environ.get("PI_CODING_AGENT_DIR") or "~/.pi/agent").expanduser()
    models_path, settings_path = directory / "models.json", directory / "settings.json"
    models = _read(models_path)
    providers = models.setdefault("providers", {})
    if not isinstance(providers, dict):
        raise ValueError(f"{models_path}: providers must be an object")
    existing = providers.get(PROVIDER, {})
    if not isinstance(existing, dict):
        raise ValueError(f"{models_path}: {PROVIDER} must be an object")
    entries = existing.get("models", [])
    if not isinstance(entries, list) or any(not isinstance(m, dict) or not isinstance(m.get("id"), str) for m in entries):
        raise ValueError(f"{models_path}: {PROVIDER}.models must be a list of model objects with IDs")
    generated = provider(s)
    generated["models"] = [m for m in entries if m["id"] != s.served_name] + generated["models"]
    providers[PROVIDER] = {**existing, **generated}
    models.setdefault("$schema", "https://pi.dev/schemas/models.schema.json")
    desired = {models_path: models}
    if make_default:
        settings = _read(settings_path)
        settings.update(defaultProvider=PROVIDER, defaultModel=s.served_name)
        desired[settings_path] = settings
    # Validate every input before creating directories, backups, or changing either file.
    changed = {path: value for path, value in desired.items() if not path.exists() or _read(path) != value}
    if not changed:
        return [f"Pi is already configured at {directory}"]
    directory.mkdir(parents=True, exist_ok=True)
    messages = []
    if any(path.exists() for path in changed):
        backup = directory / ("backup-local-deepseek-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        backup.mkdir(mode=0o700)
        for path in changed:
            if path.exists():
                shutil.copy2(path, backup / path.name)
        messages.append(f"Backup: {backup}")
    for path, value in changed.items():
        _write(path, value)
        messages.append(f"Updated: {path}")
    messages.append(f"Pi model: {PROVIDER}/{s.served_name} at {s.url}")
    return messages
