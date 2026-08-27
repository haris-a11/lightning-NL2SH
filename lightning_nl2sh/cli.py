"""Command line interface (manual sys.argv parsing, on purpose)."""

import getpass
import os
import sys

from . import __version__
from .config import KEY, config_path, key_source, load, mask, set_key
from .core import DEFAULT_MODEL, detect_shell, generate_command, shell_guessed

USAGE = """usage:
  lightning-nl2sh [--shell SHELL] [--] <task>   generate a command for <task>
  lightning-nl2sh set-key [KEY]                 store your OpenRouter API key
  lightning-nl2sh config                        show the active configuration
  lightning-nl2sh --version
  lightning-nl2sh --help

The generated command is the only thing written to stdout; errors go to stderr
and exit 1, so shell integrations can stop on failure."""


def die(message):
    print(message, file=sys.stderr)
    return 1


def cmd_set_key(args):
    if args:
        value = args[0]
        print(
            "warning: a key passed as an argument may be stored in your shell history",
            file=sys.stderr,
        )
    else:
        value = getpass.getpass("OpenRouter API key: ")
    try:
        path = set_key(value)
    except (ValueError, OSError) as exc:
        return die("error: {}".format(exc))
    print("saved {} to {}".format(mask(os.environ[KEY]), path))
    return 0


def cmd_config():
    path = config_path()
    api_key = os.environ.get(KEY)
    shell = detect_shell()
    print("config file: {} ({})".format(path, "exists" if path.exists() else "missing"))
    print("api key:     {}".format(mask(api_key)))
    print("key source:  {}".format(key_source()))
    print(
        "shell:       {}{}".format(
            shell, "  (guessed from $SHELL/platform)" if shell_guessed() else ""
        )
    )
    print("model:       {}".format(os.environ.get("NL2SH_MODEL", DEFAULT_MODEL)))
    if not api_key:
        return die("no API key configured - run: lightning-nl2sh set-key")
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    load()

    if args and args[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    if args and args[0] in ("-V", "--version"):
        print(__version__)
        return 0
    if args and args[0] == "set-key":
        return cmd_set_key(args[1:])
    if args and args[0] == "config":
        return cmd_config()

    shell = None
    while args and args[0].startswith("-"):
        if args[0] == "--":
            args.pop(0)
            break
        if args[0] == "--shell" and len(args) > 1:
            args.pop(0)
            shell = args.pop(0)
            continue
        return die("error: unknown option {}\n\n{}".format(args[0], USAGE))

    task = " ".join(args).strip()
    if not task:
        return die(USAGE)
    try:
        print(generate_command(task, shell))
    except Exception as exc:
        return die("error: {}".format(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
