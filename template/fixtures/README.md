# Encoder fixtures

The five input/output pairs are copied without modification from
[DeepSeek-V4.1-Flash-1017, revision 1bae0e1088993b9b82de08f59de5be5a34e42170](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/tree/1bae0e1088993b9b82de08f59de5be5a34e42170/encoding/tests).
The release's MIT license is included as `LICENSE` with normalized line endings; `sha256.json` records the fixture byte hashes. The files were
also checked against the release tree's Git blob IDs when imported.

From the repository root, install the optional checker dependency and run all fixture and request-shape comparisons:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-check.txt
.venv/bin/python template/check.py
```

No checkpoint, GPU or running server is needed for this check. `--native` additionally requires the separately built
`template/render_native` executable. The vendored fixtures deliberately live with the checker, independently of the
ignored reference test directory.
