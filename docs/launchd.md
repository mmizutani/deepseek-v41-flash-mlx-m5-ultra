# Login service configuration

Generate the unit with `python3 -m mac launchd --port 8888`. It is written with mode `0600`, since it can contain a
server credential. The command creates the LaunchAgents and log directories but does not load or restart a service.
Its PATH includes Apple Silicon and Intel Homebrew locations.

The unit preserves explicit environment overrides for recipe settings, plus the effective API key and native
`TENSORFOLD_API_KEY` when present. Unrelated environment variables are not copied. Regenerate and reload the unit
after changing those overrides or rotating a credential. Values not captured as overrides continue to load from
the recipe and local configuration at startup. The generated unit always serves `0.0.0.0` on its requested port;
generation reports a warning if no API key is configured.
