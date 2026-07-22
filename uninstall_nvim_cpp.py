#!/usr/bin/env python3
"""
Undo changes made by install_nvim_cpp_012.py as safely as possible.

What it does:
- Removes the current ~/.config/nvim created by the installer
- Restores the newest ~/.config/nvim.backup-* directory, when present
- Removes the exact ~/.bashrc block added by the installer
- Optionally removes Neovim plugin/data/cache directories

Usage:
    python3 uninstall_nvim_cpp.py

Notes:
- The installer only backed up ~/.config/nvim. It did not back up Neovim data,
  cache, or state directories, so those cannot be restored exactly.
- Plugin/data deletion is optional because those directories may contain files
  that existed before this setup.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "nvim"
CONFIG_PARENT = CONFIG_DIR.parent
BASHRC = HOME / ".bashrc"

MARKER = "# Use the normal user Neovim configuration"
UNSET_LINE = "unset VIMINIT"

OPTIONAL_DIRS = [
    HOME / ".local" / "share" / "nvim" / "lazy",
    HOME / ".cache" / "nvim",
    HOME / ".local" / "state" / "nvim",
]


def ask(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    answer = input(prompt + suffix).strip().lower()

    if not answer:
        return not default_no

    return answer in {"y", "yes"}


def remove_bashrc_block() -> bool:
    if not BASHRC.exists():
        return False

    lines = BASHRC.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    removed = False
    index = 0

    while index < len(lines):
        if lines[index].strip() == MARKER:
            removed = True
            index += 1

            if index < len(lines) and lines[index].strip() == UNSET_LINE:
                index += 1

            if new_lines and new_lines[-1] == "":
                new_lines.pop()

            continue

        new_lines.append(lines[index])
        index += 1

    if removed:
        content = "\n".join(new_lines).rstrip() + "\n"
        BASHRC.write_text(content, encoding="utf-8")

    return removed


def newest_backup() -> Path | None:
    backups = [
        path
        for path in CONFIG_PARENT.glob("nvim.backup-*")
        if path.is_dir()
    ]

    if not backups:
        return None

    return max(backups, key=lambda path: path.stat().st_mtime)


def remove_current_config() -> None:
    if not CONFIG_DIR.exists():
        return

    if not ask(f"Remove current Neovim config at {CONFIG_DIR}?"):
        raise RuntimeError("Cannot restore a backup while current config remains")

    shutil.rmtree(CONFIG_DIR)
    print(f"Removed: {CONFIG_DIR}")


def restore_backup() -> None:
    backup = newest_backup()

    if backup is None:
        print("No ~/.config/nvim.backup-* directory was found.")
        print("The user Neovim config will remain absent after uninstall.")
        return

    if ask(f"Restore newest backup {backup.name}?"):
        shutil.move(str(backup), str(CONFIG_DIR))
        print(f"Restored: {backup} -> {CONFIG_DIR}")
    else:
        print(f"Backup kept at: {backup}")


def optionally_remove_generated_data() -> None:
    print("\nOptional cleanup")
    print("These locations may contain Neovim files that predate this setup.")

    for path in OPTIONAL_DIRS:
        if not path.exists():
            continue

        if ask(f"Remove {path}?"):
            shutil.rmtree(path)
            print(f"Removed: {path}")
        else:
            print(f"Kept: {path}")


def main() -> int:
    print("Neovim C++ setup uninstaller")
    print("This will restore the newest config backup when available.\n")

    remove_current_config()
    restore_backup()

    if remove_bashrc_block():
        print(f"Removed installer VIMINIT block from: {BASHRC}")
    else:
        print("Installer VIMINIT block was not present in ~/.bashrc")

    optionally_remove_generated_data()

    print("\nDone.")
    print("Open a new shell or run: source ~/.bashrc")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
