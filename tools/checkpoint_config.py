"""Checkpoint metadata shared by conversion and its lightweight regression checks."""


def engram_files(layer_ids: list[int], parts: set[str], existing: dict) -> dict:
    """Keep split table references when a partial conversion did not rewrite the tables."""
    if "engram" not in parts and "engram_files" in existing:
        return existing["engram_files"]
    return {str(layer): f"engram/layer{layer}.safetensors" for layer in layer_ids}
