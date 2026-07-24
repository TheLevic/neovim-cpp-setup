# User-local Neovim for C++ on RHEL 9

No `sudo`, `dnf`, or `yum`. The installer places everything it controls under your home directory.

## Install

```bash
python3 install_nvim.py install --fresh
source ~/.bashrc
nvim
```

`--fresh` permanently deletes the existing user-level Neovim config, plugins, cache, state, and user-local Neovim installation. It does not create a backup.

## Commands

```bash
python3 install_nvim.py install --fresh
python3 install_nvim.py update
python3 install_nvim.py doctor
python3 install_nvim.py clean
python3 install_nvim.py uninstall
```

## Included

- Latest stable official Neovim Linux tarball
- Existing `clangd` and `clang-format` preferred when found on `PATH`
- Mason used as a fallback for missing C++ tools
- C/C++ completion, signatures, snippets, and inlay hints
- Diagnostics, definitions, references, rename, and code actions
- Format on save
- Treesitter
- Telescope
- Gitsigns
- Trouble
- Oil
- Aerial
- ToggleTerm
- Which-Key
- TODO comments
- Lualine
- Flash navigation

GDB stays in your terminal. CMake/build integration is intentionally deferred, so continue using:

```bash
gdev full-build-debug
```

## Main keys

| Keys | Action |
|---|---|
| `Space f f` | Find files |
| `Space f g` | Search project text |
| `Space f s` | Document symbols |
| `gd` | Definition |
| `gr` | References |
| `K` | Hover docs |
| `Space l r` | Rename |
| `Space l a` | Code action |
| `Space l f` | Format |
| `Space x x` | Diagnostics |
| `Space l o` | Symbol outline |
| `-` | File browser |
| `Space t t` | Terminal |

Press `Space` and pause to view available mappings.

## CMake / clangd

Generate a compilation database:

```bash
cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

`clangd` generally discovers `build/compile_commands.json`. When a project requires it at the root:

```bash
ln -s build/compile_commands.json compile_commands.json
```

The installer respects project `.clangd`, `.clang-format`, and `.clang-tidy` files.

## Fresh install behavior

```bash
python3 install_nvim.py install --fresh
```

This permanently removes:

- `~/.config/nvim`
- `~/.local/share/nvim`
- `~/.cache/nvim`
- `~/.local/state/nvim`
- `~/.local/nvim`
- `~/.local/bin/nvim`

It does not touch projects, system packages, compilers, CMake, GDB, or `gdev`.

## Log

```text
~/.local/state/nvim-installer/install.log
```

If headless plugin setup is blocked by network policy, open Neovim and run:

```vim
:Lazy sync
:MasonToolsInstall
:TSUpdate
:checkhealth
```
