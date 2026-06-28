# mesh_exporter — Blender extension

A Blender add-on/extension. **Only runtime code ships** in the published package; everything
else must be kept out of the built `.zip`.

## Packaging rules (the extension was delisted once for breaking these)

1. **Dev/test/tooling files must be PHYSICALLY ABSENT from the repo at build time — not just
   listed in `blender_manifest.toml` `paths_exclude_pattern`.**
   The extensions store reviewer inspects the built `.zip` directly, and the manifest's glob
   patterns only catch what they explicitly name. Files like `pytest.ini`, `ruff.toml`,
   `conftest.py`, `run_tests.sh`, `test-requirements.txt`, `tests/`, and `get-pip.py` shipped
   once *because no pattern matched them*, and the extension was delisted. Do not reintroduce
   pytest/ruff/test/CI/editor config into the tree expecting the manifest to hide it. If a tool
   config is genuinely needed for local dev, keep it outside this repo.

2. **Do not initialise logging by default.** No module-level
   `logging.getLogger(...).addHandler(...)` / `setLevel(...)`. It spams end users' consoles and
   was a delisting reason. User-facing feedback goes through Blender's `self.report()` in
   operators only. (All prior `logger.*` calls were stripped in commit `4af9d0f`.)

## Before publishing — verify the built package

```sh
blender --command extension build      # produces the .zip from blender_manifest.toml
unzip -l mesh_exporter-*.zip           # inspect contents
```

The listing must contain ONLY runtime `.py` modules + `presets/` + `LICENSE` + `README.md`.
Quick check — this should print `clean`:

```sh
unzip -l mesh_exporter-*.zip | grep -Ei 'claude|pytest|ruff|conftest|tests/|\.sh$|get-pip' || echo clean
```

If anything matches, **delete it from the repo** (don't just patch the manifest) and rebuild.

Note: this file (`CLAUDE.md`) and `ARCHITECTURE.md` are kept out of the zip via
`paths_exclude_pattern` in `blender_manifest.toml` — if you rename or add docs, add them there
too and re-run the check above.
