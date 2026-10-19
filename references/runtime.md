# Python runtime

The collection script requires Python >=3.10 and timezone data, with no third-party Python packages.

Discover candidate interpreters with `command -v python3` and versioned names available in the environment, such as `python3.14`, `python3.13`, `python3.12`, `python3.11`, or `python3.10`. On macOS, also check existing installations under `/opt/homebrew/bin`, `/usr/local/bin`, or `/Library/Frameworks/Python.framework/Versions/*/bin`; elsewhere, check the package manager or virtual environment. Check each candidate you consider with its own `--version`.

Record the selected absolute executable path and verify it before running scripts or tests:

```sh
PYTHON=/absolute/path/to/selected/python
"$PYTHON" -c 'import sys; print(sys.executable, sys.version); assert sys.version_info >= (3, 10), "Python >=3.10 required"'
```

Use this same executable for subsequent Python commands. If no interpreter qualifies, report the missing requirement.

Verify the requested `--timezone` if Python reports missing timezone data; the default is `Asia/Shanghai`:

```sh
"$PYTHON" -c 'from zoneinfo import ZoneInfo; print(ZoneInfo("Asia/Shanghai"))'
```

If the zone is unavailable, use an environment with IANA timezone data or install the system timezone database or Python `tzdata` package through the environment's normal dependency process. Do not silently substitute UTC for the requested timezone.
