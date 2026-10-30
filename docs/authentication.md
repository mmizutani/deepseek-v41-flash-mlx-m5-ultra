# Server authentication

Set `[serve] api_key` in your private `local.toml`, or supply `API_KEY` in the environment when starting the server.
`up` writes this literal value to `server-api-key` under `tf_cache`, using a private (`0600`) file in the engine's
labelled key format, and passes only its path via `--api-key-file`. Commas and colons in the configured key stay
literal. Protect both your local settings and this cache file. It remains available for the server's key-file reloads.
`python3 -m mac chat` uses the same credential. A native `TENSORFOLD_API_KEY` environment value is also accepted when
the recipe key is empty; for the native comma-separated list, `chat` selects its first nonempty key.

`command` and `validate` do not print the configured key. The printed command references the cache key file that
`up` prepares; printing a command alone does not create that file. For manual startup before the first `up`, create
that file with mode `0600` and one line `wrapper:YOUR_KEY`, or use `up` to prepare and start the server normally.

Avoid putting credentials in `extra_args`: it is an explicit raw engine-argument escape hatch. For login services,
ensure the generated launchd unit has the intended credential; an interactive shell's environment is not inherited
automatically at login.
