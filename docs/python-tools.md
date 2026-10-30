# Optional Python tools

Serving a downloaded TensorFold checkpoint and running the wrapper unit tests use only the Python standard library.
The conversion and analysis tools have separate optional dependencies; install them in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-convert.txt   # Apple Silicon conversion
# Or, for CPU reference / KL comparisons without MLX:
.venv/bin/python -m pip install -r requirements-reference.txt
```

The reference group includes NumPy, Torch, tokenizers, SymPy (Engram layout), and Pillow (image processing).
The conversion group adds MLX. These manifests declare dependencies, not a locked benchmark environment: record
the installed versions alongside any measurements. `native_kl.py` also needs the native forward binary and study
artifacts named in its help text; installing packages does not generate those inputs.

Run the lightweight checks without downloading weights or compiling the engine:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q mac tools template tests
```

GitHub Actions runs these checks on Linux and macOS. GPU inference, full conversion, native template checks and
quality/performance benchmarks remain explicit hardware-dependent checks; the unit-test workflow does not claim
to validate their numerical results.
