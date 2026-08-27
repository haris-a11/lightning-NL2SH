"""lightning-nl2sh: natural language to a command for the shell you are actually in."""

__version__ = "0.1.0"

from .config import config_path, key_source, load, mask, set_key
from .core import build_system_prompt, describe_platform, detect_shell, generate_command

__all__ = [
    "__version__",
    "build_system_prompt",
    "config_path",
    "describe_platform",
    "detect_shell",
    "generate_command",
    "key_source",
    "load",
    "mask",
    "set_key",
]
