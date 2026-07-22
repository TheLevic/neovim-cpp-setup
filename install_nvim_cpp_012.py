#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "nvim"

INIT_LUA = r'''
vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

local opt = vim.opt
opt.number = true
opt.relativenumber = true
opt.mouse = "a"
opt.expandtab = true
opt.shiftwidth = 4
opt.tabstop = 4
opt.smartindent = true
opt.ignorecase = true
opt.smartcase = true
opt.splitbelow = true
opt.splitright = true
opt.termguicolors = true
opt.signcolumn = "yes"
opt.undofile = true
opt.swapfile = false
opt.updatetime = 250
opt.timeoutlen = 500
opt.completeopt = { "menu", "menuone", "noselect" }

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"

if not vim.uv.fs_stat(lazypath) then
  local output = vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })

  if vim.v.shell_error ~= 0 then
    error("Could not install lazy.nvim:\n" .. output)
  end
end

vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  {
    "neovim/nvim-lspconfig",
    dependencies = { "saghen/blink.cmp" },
    config = function()
      vim.lsp.config("clangd", {
        cmd = {
          "clangd",
          "--background-index",
          "--clang-tidy",
          "--completion-style=detailed",
          "--header-insertion=iwyu",
        },
        capabilities = require("blink.cmp").get_lsp_capabilities(),
        root_markers = {
          "compile_commands.json",
          "compile_flags.txt",
          "CMakeLists.txt",
          ".git",
        },
      })

      vim.lsp.enable("clangd")

      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(event)
          local function map(lhs, rhs, desc)
            vim.keymap.set("n", lhs, rhs, {
              buffer = event.buf,
              desc = desc,
            })
          end

          map("gd", vim.lsp.buf.definition, "Go to definition")
          map("gr", vim.lsp.buf.references, "Find references")
          map("K", vim.lsp.buf.hover, "Show documentation")
          map("<leader>lr", vim.lsp.buf.rename, "Rename symbol")
          map("<leader>la", vim.lsp.buf.code_action, "Code action")
          map("<leader>ld", vim.diagnostic.open_float, "Show diagnostic")
        end,
      })
    end,
  },

  {
    "saghen/blink.cmp",
    version = "1.*",
    opts = {
      keymap = { preset = "default" },
      completion = {
        documentation = { auto_show = true },
      },
      sources = {
        default = { "lsp", "path", "snippets", "buffer" },
      },
    },
  },

  { "nvim-lua/plenary.nvim", lazy = true },

  {
    "nvim-telescope/telescope.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    cmd = "Telescope",
    keys = {
      { "<leader>ff", "<cmd>Telescope find_files<cr>", desc = "Find files" },
      { "<leader>fg", "<cmd>Telescope live_grep<cr>", desc = "Search text" },
      { "<leader>fb", "<cmd>Telescope buffers<cr>", desc = "Open buffers" },
      { "<leader>fr", "<cmd>Telescope oldfiles<cr>", desc = "Recent files" },
    },
    opts = {},
  },

  {
    "nvim-neo-tree/neo-tree.nvim",
    branch = "v3.x",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "MunifTanjim/nui.nvim",
      "nvim-tree/nvim-web-devicons",
    },
    keys = {
      { "<leader>e", "<cmd>Neotree toggle<cr>", desc = "Toggle explorer" },
      { "<leader>E", "<cmd>Neotree reveal<cr>", desc = "Reveal current file" },
    },
    opts = {
      filesystem = {
        follow_current_file = { enabled = true },
        filtered_items = {
          hide_dotfiles = false,
          hide_gitignored = false,
        },
      },
    },
  },

  {
    "lewis6991/gitsigns.nvim",
    event = { "BufReadPre", "BufNewFile" },
    opts = {
      on_attach = function(bufnr)
        local gs = require("gitsigns")

        local function map(lhs, rhs, desc)
          vim.keymap.set("n", lhs, rhs, {
            buffer = bufnr,
            desc = desc,
          })
        end

        map("]c", function()
          if vim.wo.diff then
            vim.cmd.normal({ "]c", bang = true })
          else
            gs.nav_hunk("next")
          end
        end, "Next Git change")

        map("[c", function()
          if vim.wo.diff then
            vim.cmd.normal({ "[c", bang = true })
          else
            gs.nav_hunk("prev")
          end
        end, "Previous Git change")

        map("<leader>gp", gs.preview_hunk, "Preview Git hunk")
        map("<leader>gs", gs.stage_hunk, "Stage Git hunk")
        map("<leader>gr", gs.reset_hunk, "Reset Git hunk")
        map("<leader>gb", gs.blame_line, "Git blame line")
      end,
    },
  },

  {
    "sindrets/diffview.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    cmd = { "DiffviewOpen", "DiffviewClose", "DiffviewFileHistory" },
    keys = {
      { "<leader>ga", "<cmd>DiffviewOpen<cr>", desc = "Diff all changed files" },
      { "<leader>gd", "<cmd>DiffviewOpen -- %<cr>", desc = "Diff current file" },
      { "<leader>gc", "<cmd>DiffviewClose<cr>", desc = "Close Git diff" },
      { "<leader>gh", "<cmd>DiffviewFileHistory %<cr>", desc = "File history" },
    },
    opts = {
      enhanced_diff_hl = true,
      view = {
        default = { layout = "diff2_horizontal" },
      },
    },
  },

  {
    "folke/which-key.nvim",
    event = "VeryLazy",
    opts = {
      spec = {
        { "<leader>f", group = "Find" },
        { "<leader>g", group = "Git" },
        { "<leader>c", group = "Build" },
        { "<leader>l", group = "Language" },
      },
    },
  },

  {
    "Civitasv/cmake-tools.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    ft = { "cmake", "c", "cpp" },
    keys = {
      { "<leader>cc", "<cmd>CMakeGenerate<cr>", desc = "CMake configure" },
      { "<leader>cm", "<cmd>CMakeBuild<cr>", desc = "CMake plugin build" },
      { "<leader>cr", "<cmd>CMakeRun<cr>", desc = "CMake run" },
      { "<leader>ct", "<cmd>CMakeSelectBuildTarget<cr>", desc = "Select target" },
    },
    opts = {
      cmake_command = "cmake",
      cmake_build_directory = "build",
      cmake_generate_options = {
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
      },
      cmake_executor = { name = "quickfix", opts = {} },
      cmake_runner = { name = "terminal", opts = {} },
    },
  },
}, {
  checker = { enabled = false },
  change_detection = { notify = false },
})

local map = vim.keymap.set

map("n", "<leader>w", "<cmd>write<cr>", { desc = "Save file" })
map("n", "<leader>q", "<cmd>quit<cr>", { desc = "Quit" })
map("n", "<leader>bd", "<cmd>bdelete<cr>", { desc = "Close buffer" })
map("n", "<Esc>", "<cmd>nohlsearch<cr>", { desc = "Clear search" })

map("n", "<C-h>", "<C-w>h", { desc = "Move left" })
map("n", "<C-j>", "<C-w>j", { desc = "Move down" })
map("n", "<C-k>", "<C-w>k", { desc = "Move up" })
map("n", "<C-l>", "<C-w>l", { desc = "Move right" })

map("n", "<leader>cb", function()
  vim.cmd("botright split")
  vim.cmd("terminal x-full-build-debug")
end, { desc = "Build debug" })

map("n", "<leader>cB", function()
  vim.cmd("botright split")
  vim.cmd("terminal x-full-build")
end, { desc = "Build normal" })
'''

CHEATSHEET = r'''
NEOVIM C++ CHEAT SHEET

Leader key: Space
Press Space and pause to open Which Key.

FILES
  Space e       Explorer
  Space f f     Find file
  Space f g     Search project text
  Space f b     Open buffers

C++
  g d           Definition
  g r           References
  K             Documentation
  Space l r     Rename
  Space l a     Code action
  Space l d     Diagnostic details

GIT
  Space g a     All changed files
  Space g d     Current-file side-by-side diff
  Space g c     Close diff
  Space g h     File history
  ] c           Next changed hunk
  [ c           Previous changed hunk
  Space g p     Preview hunk
  Space g s     Stage hunk
  Space g r     Reset hunk

BUILD
  Space c b     x-full-build-debug
  Space c B     x-full-build
  Space c c     CMake configure
  Space c m     CMake plugin build

CHECKS
  :Lazy
  :checkhealth
  :checkhealth vim.lsp

COMPILE DATABASE
  ln -sfn "$PWD/build/rhel9/Debug/compile_commands.json" compile_commands.json
'''

def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

def backup_existing_config() -> Path | None:
    if not CONFIG_DIR.exists():
        return None

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CONFIG_DIR.with_name(f"nvim.backup-{stamp}")
    shutil.move(str(CONFIG_DIR), str(backup))
    return backup

def ensure_viminit_is_unset() -> None:
    bashrc = HOME / ".bashrc"
    marker = "# Use the normal user Neovim configuration"
    current = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""

    if marker not in current:
        with bashrc.open("a", encoding="utf-8") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write(f"\n{marker}\nunset VIMINIT\n")

def main() -> int:
    if not shutil.which("nvim"):
        raise RuntimeError("nvim is not available in PATH")

    if not shutil.which("git"):
        raise RuntimeError("git is not available in PATH")

    version_output = run(["nvim", "--version"]).stdout
    first_line = version_output.splitlines()[0] if version_output else "Unknown version"
    print(f"Detected: {first_line}")

    if "v0.12" not in first_line:
        answer = input(
            "This installer targets Neovim 0.12.x. Continue anyway? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 0

    if CONFIG_DIR.exists():
        answer = input(
            f"{CONFIG_DIR} exists. Back it up and replace it? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 0

    backup = backup_existing_config()
    if backup:
        print(f"Backup created: {backup}")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "init.lua").write_text(INIT_LUA.lstrip(), encoding="utf-8")
    (CONFIG_DIR / "CHEATSHEET.txt").write_text(CHEATSHEET.lstrip(), encoding="utf-8")

    ensure_viminit_is_unset()

    print(f"Config created at: {CONFIG_DIR}")
    print("Added 'unset VIMINIT' to ~/.bashrc")
    print("Installing plugins...")

    result = run([
        "env",
        "-u",
        "VIMINIT",
        "nvim",
        "--headless",
        "+Lazy! sync",
        "+qa",
    ])

    if result.returncode != 0:
        print("\nAutomatic plugin installation was incomplete.")
        print(result.stdout)
        print("Start Neovim and run :Lazy sync")
    else:
        print("Plugins installed successfully.")

    missing = [
        name for name in ("clangd", "cmake", "rg")
        if not shutil.which(name)
    ]

    if missing:
        print("\nInstall these through your custom package manager:")
        for name in missing:
            print(f"  - {name}")

    print('''
Next:

  source ~/.bashrc
  cd /path/to/project
  ln -sfn "$PWD/build/rhel9/Debug/compile_commands.json" compile_commands.json
  nvim .

Then run:
  :checkhealth
  :checkhealth vim.lsp

Press Space and pause to see key bindings.
''')
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
