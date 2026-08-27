"""Config directory and API-key storage."""

import os
from pathlib import Path

from dotenv import dotenv_values, find_dotenv, load_dotenv

KEY = "NL2SH_API_KEY"


def config_dir():
    """NL2SH_CONFIG_DIR > $XDG_CONFIG_HOME/lightning-nl2sh > ~/.config/lightning-nl2sh."""
    override = os.environ.get("NL2SH_CONFIG_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / "lightning-nl2sh"


def config_path():
    return config_dir() / ".env"


def load():
    """Project .env, then global config. override=False means the real environment
    wins over both, and the project .env wins over the global config."""
    load_dotenv(find_dotenv(usecwd=True))  # cwd-relative, not package-relative
    load_dotenv(config_path(), override=False)


def set_key(value):
    """Rewrite only the NL2SH_API_KEY line of the config .env, atomically."""
    value = value.strip().strip("'\"").strip()
    if not value:
        raise ValueError("empty API key")
    if "\n" in value or "\r" in value:
        raise ValueError("API key must not contain newlines")

    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass  # Windows

    out, written = [], False
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            head = line.strip()
            if head.startswith(KEY + "=") or head.startswith("export " + KEY + "="):
                if not written:
                    out.append("{}={}".format(KEY, value))
                    written = True
            else:
                out.append(line)
    if not written:
        out.append("{}={}".format(KEY, value))

    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.replace(str(tmp), str(path))
    os.environ[KEY] = value
    return path


def mask(value):
    if not value:
        return "(none)"
    return (value[:6] + "…" + value[-4:]) if len(value) > 12 else "…" + value[-4:]


def key_source():
    """Where the active key came from: environment, config file, or nowhere."""
    active = os.environ.get(KEY)
    if not active:
        return "nowhere"
    path = config_path()
    if path.exists() and dotenv_values(str(path)).get(KEY) == active:
        return "config file"
    return "environment"
