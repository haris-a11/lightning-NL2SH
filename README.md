# lightning-nl2sh

## 1. What it does

`lightning-nl2sh` turns a plain-English task into a shell command, using an OpenRouter model, and generates it in the syntax of **the shell you are actually using**.

```console
$ lightning-nl2sh "find all python files modified today"
find . -name '*.py' -mtime -1
```

The command is written to stdout and nothing else is. Errors go to stderr with exit code `1`, so a shell wrapper can stop cleanly when generation fails.

### Why shell-specific generation matters

| Situation               | What a generic answer gets wrong                                                                    |
| ----------------------- | --------------------------------------------------------------------------------------------------- |
| **fish**                | fish is not POSIX. `$(cmd)` must be `(cmd)`, and `export VAR=value` must be `set -x VAR value`.     |
| **PowerShell 5.1 vs 7** | Windows PowerShell 5.1 has no `&&`; commands must be chained with `;`. PowerShell 7+ supports `&&`. |
| **macOS**               | BSD userland: `sed -i` requires an argument (`sed -i '' ...`) and `stat` uses `-f`, not `-c`.       |
| **WSL**                 | Windows drives live at `/mnt/c/...`.                                                                |
| **Git Bash**            | Windows drives live at `/c/...`.                                                                    |

Supported shell IDs: `bash`, `zsh`, `fish`, `sh`, `dash`, `ksh`, `tcsh`, `csh`,
`wsl`, `gitbash`, `pwsh`, `powershell`, `cmd`. (`dash`, `ksh`, `tcsh` and `csh` are treated as `sh`.)

## 2. Install

```bash
pip install lightning-nl2sh
```

From a checkout:

```bash
pip install .
```

Then store your [OpenRouter](https://openrouter.ai/) key:

```bash
lightning-nl2sh set-key
```

## 3. Shell setup

The shell integration exports **`NL2SH_SHELL`**. That is the whole shell-detection mechanism: the shell that runs the wrapper tells the tool what it is.

The fallback, when `NL2SH_SHELL` is unset, is the basename of `$SHELL`. Note that **`$SHELL` is only your _login_ shell** — if you are in `fish` launched from a `bash` login shell, `$SHELL` still says `bash`. Set `NL2SH_SHELL` (the integrations below do it for you) or pass `--shell`.

Every integration below stops when `lightning-nl2sh` exits non-zero.

### zsh

Add to `~/.zshrc`:

```zsh
export NL2SH_SHELL=zsh

ai() {
  local cmd
  cmd=$(lightning-nl2sh "$@") || return $?
  [[ -n "$cmd" ]] || return 1
  print -z -- "$cmd"
}
```

`print -z` pushes the command onto the editable command buffer: it appears at your prompt, ready to read, edit, or discard. Nothing runs until you press Enter.

### bash

Add to `~/.bashrc` on Linux, or `~/.bash_profile` on macOS:

```bash
export NL2SH_SHELL=bash

ai() {
  local cmd
  cmd=$(lightning-nl2sh "$@") || return $?
  [[ -n "$cmd" ]] || return 1
  read -e -i "$cmd" -p "> " cmd || return 1
  [[ -n "$cmd" ]] || return 1
  history -s "$cmd"
  eval "$cmd"
}
```

bash has no `print -z`, so `read -e -i` is the equivalent: the generated command is pre-loaded into an editable readline prompt. It is your confirmation step. `history -s` puts it in your history so
Up-arrow works afterwards.

**WSL and Git Bash** use exactly the same function; only the shell ID changes, so the model knows how Windows drives are spelled:

```bash
export NL2SH_SHELL=wsl        # inside WSL: drives are /mnt/c/...
export NL2SH_SHELL=gitbash    # in Git Bash: drives are /c/...
```

### fish

Add to `~/.config/fish/config.fish`:

```fish
set -gx NL2SH_SHELL fish

function ai
    set -l cmd (lightning-nl2sh $argv) ; or return $status
    test -n "$cmd" ; or return 1
    echo $cmd
    read -l -P "run? [y/N] " reply
    test "$reply" = y -o "$reply" = Y ; or return 1
    history append -- $cmd
    eval $cmd
end
```

fish's `commandline` builtin — the only way to preload the command buffer — works **only from a key binding**, not from a normal function. So the function above prints the command and asks for an explicit `y/N` confirmation instead, and runs it only after you confirm. `history append` needs **fish 3.2+**; drop that line on older versions.

If you would rather have the zsh-style buffer behaviour, use a key binding
(Alt-A here) instead of the function:

```fish
bind \ea 'commandline -r (lightning-nl2sh (commandline) | string collect)'
```

### PowerShell

Add to `$PROFILE`:

```powershell
$env:NL2SH_SHELL = "pwsh"        # PowerShell 7+
# $env:NL2SH_SHELL = "powershell"  # Windows PowerShell 5.1

function ai {
    $cmd = lightning-nl2sh @args
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($cmd)) { return }
    Write-Host $cmd
    [Microsoft.PowerShell.PSConsoleReadLine]::AddToHistory($cmd)
}
```

`AddToHistory` puts the generated command in PSReadLine's history, so pressing **Up-arrow** recalls it into your editable prompt. Nothing is executed for you.

If the profile file does not exist yet:

```powershell
New-Item -Path $PROFILE -Force
```

Pick the shell ID that matches your version — `powershell` (5.1) makes the model chain with `;`, `pwsh` (7+) lets it use `&&`.

### cmd.exe

cmd.exe cannot reliably replace the current command-line buffer, so there is no wrapper. Call the tool directly and copy the result:

```text
lightning-nl2sh "find all Python files modified today"
```

Set `NL2SH_SHELL` once with `setx NL2SH_SHELL cmd`.

## 4. Configuration

```bash
lightning-nl2sh set-key           # prompts, never echoes, never hits your history
lightning-nl2sh set-key sk-or-... # inline; warns that this lands in shell history
lightning-nl2sh config            # show config path, masked key, shell, model
```

`config` exits `1` when no API key is configured.

The config file is `<config dir>/.env`, where the config directory is the first of:

1. `NL2SH_CONFIG_DIR`
2. `$XDG_CONFIG_HOME/lightning-nl2sh`
3. `~/.config/lightning-nl2sh` (works on Windows too — `Path.home()`)

It is written atomically and created with mode `0600` where the OS supports it.
`set-key` rewrites only the `OPENROUTER_API_KEY` line; comments and every other variable in the file are preserved.

Environment variables:

| Variable             | Meaning                                                            |
| -------------------- | ------------------------------------------------------------------ |
| `OPENROUTER_API_KEY` | API key. A real environment variable always beats the config file. |
| `NL2SH_MODEL`        | Model slug. Default `qwen/qwen3-14b`.                              |
| `NL2SH_SHELL`        | Shell ID, exported by the shell integration.                       |
| `NL2SH_CONFIG_DIR`   | Override the config directory.                                     |

## 5. Direct use

```bash
lightning-nl2sh "compress this folder into a tarball"
lightning-nl2sh --shell fish "list every file larger than 100MB"
lightning-nl2sh -- "-n flag examples for grep"   # -- when the task starts with -
```

`--shell` overrides detection, which is handy for generating a command for a machine you are about to SSH into.

## 6. Safety

**Commands are model-generated and unverified. Read every command before you run it.** The model can hallucinate flags, misread your intent, or produce something destructive that looks reasonable.

Be especially careful with anything involving:

- `rm`, `rmdir`, `dd`, `mkfs`, `shred`
- output redirection (`>`, `>>`) that overwrites files
- permission and ownership changes (`chmod`, `chown`, `icacls`)
- anything recursive, anything with a wildcard, anything run with `sudo`
- filesystem-wide operations, `find ... -delete`, `find ... -exec`

The `ai` shell function must **never** execute the generated command automatically, unless the integration for that shell explicitly asks for confirmation first. The zsh and PowerShell integrations above never execute anything — they hand you an editable line. The bash integration stops at an editable readline prompt, and the fish integration stops at a `y/N` prompt. If you write your own wrapper, keep that property.
