import os
import sys

import requests

from .config import KEY

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-14b"

ALIASES = {"dash": "sh", "ksh": "sh", "tcsh": "sh", "csh": "sh"}

# shell id -> (description, chaining operator)
PROFILES = {
    "bash": ("GNU bash, POSIX-compatible. $() and export VAR=value work.", "&&"),
    "zsh": ("zsh, POSIX-compatible. $() and export VAR=value work.", "&&"),
    "sh": (
        "POSIX sh (dash/ksh/csh family). Portable POSIX syntax only; no bashisms "
        "like [[ ]], arrays or process substitution.",
        "&&",
    ),
    "fish": (
        "fish, NOT POSIX. Use (cmd) instead of $(cmd), and set -x VAR value instead "
        "of export VAR=value. Never use export or $().",
        "&&",
    ),
    "wsl": (
        "bash inside WSL. Windows drives are mounted at /mnt/c/..., not C:\\.",
        "&&",
    ),
    "gitbash": ("Git Bash (MSYS2). Windows drives are /c/..., not C:\\.", "&&"),
    "pwsh": ("PowerShell 7+. Cmdlets and .NET types; && and || are supported.", "&&"),
    "powershell": ("Windows PowerShell 5.1: it does NOT support && or ||; use ;", ";"),
    "cmd": ("Windows cmd.exe. Use %VAR% for variables and backslash paths.", "&&"),
}
PROFILES.update({alias: PROFILES["sh"] for alias in ALIASES})


def detect_shell():
    """NL2SH_SHELL (set by the shell integration) > basename($SHELL) > platform default.

    $SHELL is only the *login* shell and may not be the shell running this command,
    which is why the shell integration exports NL2SH_SHELL.
    """
    shell = os.environ.get("NL2SH_SHELL") or os.path.basename(
        os.environ.get("SHELL", "")
    )
    if not shell:
        shell = "powershell" if os.name == "nt" else "sh"
    return shell.lower()


def shell_guessed():
    """True when the shell was inferred from $SHELL/platform rather than NL2SH_SHELL."""
    return not os.environ.get("NL2SH_SHELL")


def describe_platform():
    if sys.platform == "win32":
        return "Windows"
    if sys.platform == "darwin":
        return (
            "macOS (BSD userland: sed -i requires an argument, e.g. sed -i '' ...; "
            "stat uses -f not -c)"
        )
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "Linux"


def build_system_prompt(shell):
    description, chain = PROFILES.get(ALIASES.get(shell, shell), PROFILES["sh"])
    return (
        "You translate natural-language tasks into a single shell command.\n"
        "Target shell: {shell}\n"
        "Shell notes: {description}\n"
        "Platform: {platform}\n"
        "Generate syntax valid for that exact shell and platform.\n"
        "Return ONLY the command. No Markdown, no backticks, no code fences, "
        "no explanation, no preamble.\n"
        "If several commands are needed, chain them with {chain}"
    ).format(
        shell=shell, description=description, platform=describe_platform(), chain=chain
    )


def base_url():
    """Any OpenAI-compatible /chat/completions endpoint. Trailing slash tolerated."""
    return os.environ.get("NL2SH_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def model():
    return os.environ.get("NL2SH_MODEL", DEFAULT_MODEL)


def generate_command(task, shell=None):

    shell = (shell or detect_shell()).lower()
    url, name = base_url(), model()
    api_key = os.environ.get(KEY)
    if not api_key:
        raise RuntimeError("no {} - run: lightning-nl2sh set-key".format(KEY))

    prompt = ("/no_think\n" + task) if "qwen" in name.lower() else task
    payload = {
        "model": name,
        "messages": [
            {"role": "system", "content": build_system_prompt(shell)},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 100,
    }
    if "openrouter.ai" in url:

        payload["reasoning"] = {"effort": "none"}

    response = requests.post(
        url + "/chat/completions",
        headers={"Authorization": "Bearer " + api_key},
        json=payload,
        timeout=30,
    )
    if not response.ok:

        raise RuntimeError(
            "{} from {}: {}".format(response.status_code, url, response.text[:300])
        )
    text = response.json()["choices"][0]["message"]["content"] or ""
    kept = [ln for ln in text.strip().splitlines() if not ln.strip().startswith("```")]
    return "\n".join(kept).strip()
