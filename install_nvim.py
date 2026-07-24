#!/usr/bin/env python3
# User-local Neovim + C++ installer for RHEL 9. Never uses sudo.
# Prefers existing clangd/clang-format on PATH; Mason is a fallback.

from __future__ import annotations
import argparse, datetime as dt, json, os, platform, shutil, subprocess
import sys, tarfile, tempfile, urllib.request
from pathlib import Path

HOME = Path.home()
LOCAL = HOME / ".local"
BIN = LOCAL / "bin"
NVIM_ROOT = LOCAL / "nvim"
CONFIG = HOME / ".config" / "nvim"
DATA = LOCAL / "share" / "nvim"
CACHE = HOME / ".cache" / "nvim"
STATE = LOCAL / "state" / "nvim"
LOG = LOCAL / "state" / "nvim-installer" / "install.log"
BASHRC = HOME / ".bashrc"
BEGIN = "# >>> user-local-neovim >>>"
END = "# <<< user-local-neovim <<<"
UA = "nvim-cpp-rhel9-installer/1.0"

def emit(prefix, msg):
    print(f"{prefix} {msg}")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {prefix} {msg}\n")

def info(msg): emit("→", msg)
def ok(msg): emit("✓", msg)
def warn(msg): emit("!", msg)
def fail(msg): emit("✗", msg)

def run(args, check=True, capture=False, env=None):
    with LOG.open("a", encoding="utf-8") as f:
        f.write("$ " + " ".join(map(str, args)) + "\n")
    return subprocess.run(
        [str(x) for x in args], check=check, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None, env=env
    )

def cmd(name):
    local = BIN / name
    if local.exists() and os.access(local, os.X_OK):
        return str(local)
    return shutil.which(name)

def atomic_write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.chmod(mode)
    tmp.replace(path)

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r, path.open("wb") as f:
        shutil.copyfileobj(r, f)

def arch_token():
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"): return "linux-x86_64"
    if machine in ("aarch64", "arm64"): return "linux-arm64"
    raise RuntimeError(f"Unsupported CPU architecture: {machine}")

def latest_neovim():
    release = fetch_json("https://api.github.com/repos/neovim/neovim/releases/latest")
    token = arch_token()
    assets = [
        a for a in release.get("assets", [])
        if token in a.get("name", "") and a.get("name", "").endswith(".tar.gz")
    ]
    if not assets:
        raise RuntimeError(f"No official {token} Neovim tarball found")
    assets.sort(key=lambda a: len(a["name"]))
    return release["tag_name"], assets[0]["browser_download_url"], assets[0]["name"]

def install_neovim():
    version, url, name = latest_neovim()
    nvim = BIN / "nvim"
    if nvim.exists():
        p = run([nvim, "--version"], check=False, capture=True)
        if p.stdout and version in p.stdout.splitlines()[0]:
            ok(f"Neovim {version} already installed")
            return version
    info(f"Installing Neovim {version}")
    with tempfile.TemporaryDirectory(prefix="nvim-install-") as td:
        td = Path(td)
        archive = td / name
        download(url, archive)
        extract = td / "extract"
        extract.mkdir()
        with tarfile.open(archive, "r:gz") as tf:
            root = extract.resolve()
            for m in tf.getmembers():
                p = (extract / m.name).resolve()
                if p != root and root not in p.parents:
                    raise RuntimeError(f"Unsafe archive path: {m.name}")
            tf.extractall(extract)
        dirs = [p for p in extract.iterdir() if p.is_dir()]
        if len(dirs) != 1: raise RuntimeError("Unexpected Neovim archive layout")
        old = NVIM_ROOT.with_name("nvim.old")
        shutil.rmtree(old, ignore_errors=True)
        if NVIM_ROOT.exists(): NVIM_ROOT.rename(old)
        try:
            shutil.move(str(dirs[0]), str(NVIM_ROOT))
        except Exception:
            if old.exists() and not NVIM_ROOT.exists(): old.rename(NVIM_ROOT)
            raise
        shutil.rmtree(old, ignore_errors=True)
    BIN.mkdir(parents=True, exist_ok=True)
    if nvim.exists() or nvim.is_symlink(): nvim.unlink()
    nvim.symlink_to(NVIM_ROOT / "bin" / "nvim")
    ok(f"Installed {version} under {NVIM_ROOT}")
    return version

def update_bashrc():
    block = (
        f"{BEGIN}\n"
        '# Neovim user-local executable.\n'
        'export PATH="$HOME/.local/bin:$PATH"\n'
        f"{END}\n"
    )
    text = BASHRC.read_text(encoding="utf-8") if BASHRC.exists() else ""
    if BEGIN in text and END in text:
        before = text.split(BEGIN, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip("\n")
        text = before + "\n\n" + block + (("\n" + after) if after else "")
    else:
        text = text.rstrip() + (("\n\n" if text.strip() else "")) + block
    atomic_write(BASHRC, text)
    ok("Updated ~/.bashrc PATH")

FILES = {
"init.lua": r'''vim.g.mapleader = " "
vim.g.maplocalleader = "\\"
require("config.options")
require("config.keymaps")
require("config.project")
require("config.lazy")
''',

"lua/config/options.lua": r'''local o = vim.opt
o.number = true
o.relativenumber = true
o.mouse = "a"
o.breakindent = true
o.undofile = true
o.ignorecase = true
o.smartcase = true
o.signcolumn = "yes"
o.updatetime = 250
o.timeoutlen = 400
o.splitright = true
o.splitbelow = true
o.completeopt = { "menu", "menuone", "noselect" }
o.termguicolors = true
o.cursorline = true
o.scrolloff = 6
o.expandtab = true
o.shiftwidth = 2
o.tabstop = 2
vim.diagnostic.config({
  severity_sort = true,
  underline = true,
  update_in_insert = false,
  virtual_text = { spacing = 2, prefix = "●" },
  float = { border = "rounded", source = true },
})
''',

"lua/config/keymaps.lua": r'''local m = vim.keymap.set
m("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Clear search" })
m("n", "<leader>w", "<cmd>write<CR>", { desc = "Save" })
m("n", "-", "<cmd>Oil<CR>", { desc = "Parent directory" })
m("n", "<leader>tt", "<cmd>ToggleTerm<CR>", { desc = "Terminal" })
m("t", "<Esc><Esc>", [[<C-\><C-n>]], { desc = "Normal mode" })
m("n", "<C-h>", "<C-w><C-h>", { desc = "Window left" })
m("n", "<C-j>", "<C-w><C-j>", { desc = "Window down" })
m("n", "<C-k>", "<C-w><C-k>", { desc = "Window up" })
m("n", "<C-l>", "<C-w><C-l>", { desc = "Window right" })
''',

"lua/config/project.lua": r'''local g = vim.api.nvim_create_augroup("CppProjectHints", { clear = true })
vim.api.nvim_create_autocmd({ "BufEnter", "DirChanged" }, {
  group = g,
  callback = function()
    local cwd = vim.uv.cwd()
    if not cwd then return end
    local build_db = cwd .. "/build/compile_commands.json"
    local root_db = cwd .. "/compile_commands.json"
    if vim.fn.filereadable(build_db) == 1 and vim.fn.filereadable(root_db) == 0
       and not vim.g.compile_commands_hint_shown then
      vim.g.compile_commands_hint_shown = true
      vim.schedule(function()
        vim.notify("Found build/compile_commands.json; clangd should discover it automatically.")
      end)
    end
  end,
})
''',

"lua/config/lazy.lua": r'''local path = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(path) then
  local out = vim.fn.system({
    "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", path,
  })
  if vim.v.shell_error ~= 0 then error("lazy.nvim clone failed:\n" .. out) end
end
vim.opt.rtp:prepend(path)
require("lazy").setup({
  spec = { { import = "plugins" } },
  checker = { enabled = true, notify = false },
  change_detection = { notify = false },
  ui = { border = "rounded" },
})
''',

"lua/plugins/lsp.lua": r'''return {
  { "mason-org/mason.nvim", cmd = "Mason", build = ":MasonUpdate", opts = {} },
  {
    "WhoIsSethDaniel/mason-tool-installer.nvim",
    dependencies = { "mason-org/mason.nvim" },
    opts = function()
      local missing = {}
      if vim.fn.executable("clangd") == 0 then table.insert(missing, "clangd") end
      if vim.fn.executable("clang-format") == 0 then table.insert(missing, "clang-format") end
      return { ensure_installed = missing, run_on_start = #missing > 0, start_delay = 500 }
    end,
  },
  {
    "neovim/nvim-lspconfig",
    event = { "BufReadPre", "BufNewFile" },
    dependencies = { "hrsh7th/cmp-nvim-lsp" },
    config = function()
      vim.lsp.config("clangd", {
        capabilities = require("cmp_nvim_lsp").default_capabilities(),
        cmd = {
          "clangd", "--background-index", "--clang-tidy",
          "--completion-style=detailed", "--header-insertion=iwyu",
          "--function-arg-placeholders",
        },
        root_markers = {
          ".clangd", ".clang-tidy", ".clang-format",
          "compile_commands.json", "compile_flags.txt",
          "CMakeLists.txt", ".git",
        },
      })
      vim.lsp.enable("clangd")
      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(e)
          local function map(k, f, d)
            vim.keymap.set("n", k, f, { buffer = e.buf, desc = "LSP: " .. d })
          end
          map("gd", vim.lsp.buf.definition, "Definition")
          map("gD", vim.lsp.buf.declaration, "Declaration")
          map("gr", vim.lsp.buf.references, "References")
          map("gi", vim.lsp.buf.implementation, "Implementation")
          map("K", vim.lsp.buf.hover, "Hover")
          map("<leader>lr", vim.lsp.buf.rename, "Rename")
          map("<leader>la", vim.lsp.buf.code_action, "Code action")
          map("<leader>ls", vim.lsp.buf.signature_help, "Signature help")
          map("[d", function() vim.diagnostic.jump({ count = -1, float = true }) end, "Previous diagnostic")
          map("]d", function() vim.diagnostic.jump({ count = 1, float = true }) end, "Next diagnostic")
          local c = vim.lsp.get_client_by_id(e.data.client_id)
          if c and c:supports_method("textDocument/inlayHint") then
            vim.lsp.inlay_hint.enable(true, { bufnr = e.buf })
          end
        end,
      })
    end,
  },
}
''',

"lua/plugins/completion.lua": r'''return {
  {
    "L3MON4D3/LuaSnip",
    version = "v2.*",
    build = vim.fn.executable("make") == 1 and "make install_jsregexp" or nil,
    dependencies = { "rafamadriz/friendly-snippets" },
    config = function() require("luasnip.loaders.from_vscode").lazy_load() end,
  },
  {
    "hrsh7th/nvim-cmp",
    event = "InsertEnter",
    dependencies = {
      "hrsh7th/cmp-nvim-lsp", "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path", "saadparwaiz1/cmp_luasnip",
      "L3MON4D3/LuaSnip",
    },
    config = function()
      local cmp, ls = require("cmp"), require("luasnip")
      cmp.setup({
        snippet = { expand = function(a) ls.lsp_expand(a.body) end },
        mapping = cmp.mapping.preset.insert({
          ["<C-n>"] = cmp.mapping.select_next_item(),
          ["<C-p>"] = cmp.mapping.select_prev_item(),
          ["<C-Space>"] = cmp.mapping.complete(),
          ["<C-e>"] = cmp.mapping.abort(),
          ["<CR>"] = cmp.mapping.confirm({ select = true }),
          ["<Tab>"] = cmp.mapping(function(f)
            if cmp.visible() then cmp.select_next_item()
            elseif ls.expand_or_jumpable() then ls.expand_or_jump()
            else f() end
          end, { "i", "s" }),
          ["<S-Tab>"] = cmp.mapping(function(f)
            if cmp.visible() then cmp.select_prev_item()
            elseif ls.jumpable(-1) then ls.jump(-1)
            else f() end
          end, { "i", "s" }),
        }),
        sources = cmp.config.sources({
          { name = "nvim_lsp" }, { name = "luasnip" }, { name = "path" },
        }, { { name = "buffer", keyword_length = 3 } }),
        window = {
          completion = cmp.config.window.bordered(),
          documentation = cmp.config.window.bordered(),
        },
      })
    end,
  },
}
''',

"lua/plugins/search.lua": r'''return {
  {
    "nvim-telescope/telescope.nvim",
    branch = "0.1.x",
    dependencies = {
      "nvim-lua/plenary.nvim",
      {
        "nvim-telescope/telescope-fzf-native.nvim",
        build = "make",
        cond = vim.fn.executable("make") == 1,
      },
    },
    keys = {
      { "<leader>ff", "<cmd>Telescope find_files hidden=true<CR>", desc = "Find files" },
      { "<leader>fg", "<cmd>Telescope live_grep<CR>", desc = "Live grep" },
      { "<leader>fb", "<cmd>Telescope buffers<CR>", desc = "Buffers" },
      { "<leader>fs", "<cmd>Telescope lsp_document_symbols<CR>", desc = "Document symbols" },
      { "<leader>fS", "<cmd>Telescope lsp_workspace_symbols<CR>", desc = "Workspace symbols" },
      { "<leader>fr", "<cmd>Telescope oldfiles<CR>", desc = "Recent files" },
    },
    config = function()
      local t = require("telescope")
      t.setup({ defaults = {
        file_ignore_patterns = { "%.git/", "build/", "cmake%-build%-" },
      } })
      pcall(t.load_extension, "fzf")
    end,
  },
}
''',

"lua/plugins/editing.lua": r'''return {
  {
    "nvim-treesitter/nvim-treesitter",
    branch = "master",
    build = ":TSUpdate",
    event = { "BufReadPost", "BufNewFile" },
    config = function()
      require("nvim-treesitter.configs").setup({
        ensure_installed = {
          "c", "cpp", "cmake", "lua", "vim", "vimdoc",
          "bash", "json", "yaml", "markdown",
        },
        auto_install = true,
        highlight = { enable = true },
        indent = { enable = true },
      })
    end,
  },
  {
    "stevearc/conform.nvim",
    event = "BufWritePre",
    keys = {{
      "<leader>lf",
      function() require("conform").format({ async = true, lsp_format = "fallback" }) end,
      desc = "Format",
    }},
    opts = {
      formatters_by_ft = { c = { "clang_format" }, cpp = { "clang_format" } },
      format_on_save = function(buf)
        if vim.g.disable_autoformat or vim.b[buf].disable_autoformat then return end
        return { timeout_ms = 1200, lsp_format = "fallback" }
      end,
    },
    init = function()
      vim.api.nvim_create_user_command("FormatDisable", function(a)
        if a.bang then vim.b.disable_autoformat = true
        else vim.g.disable_autoformat = true end
      end, { bang = true })
      vim.api.nvim_create_user_command("FormatEnable", function()
        vim.b.disable_autoformat = false
        vim.g.disable_autoformat = false
      end, {})
    end,
  },
}
''',

"lua/plugins/tools.lua": r'''return {
  {
    "folke/which-key.nvim",
    event = "VeryLazy",
    opts = { preset = "modern", spec = {
      { "<leader>f", group = "Find" },
      { "<leader>g", group = "Git" },
      { "<leader>l", group = "LSP" },
      { "<leader>x", group = "Diagnostics" },
    }},
  },
  {
    "stevearc/oil.nvim",
    cmd = "Oil",
    opts = { view_options = { show_hidden = true } },
    dependencies = { "nvim-tree/nvim-web-devicons" },
  },
  {
    "akinsho/toggleterm.nvim",
    version = "*",
    cmd = { "ToggleTerm", "TermExec" },
    opts = { direction = "float", float_opts = { border = "rounded" } },
  },
  {
    "stevearc/aerial.nvim",
    cmd = "AerialToggle",
    keys = {{ "<leader>lo", "<cmd>AerialToggle!<CR>", desc = "Symbol outline" }},
    opts = {},
    dependencies = { "nvim-tree/nvim-web-devicons" },
  },
  {
    "folke/trouble.nvim",
    cmd = "Trouble",
    opts = {},
    keys = {
      { "<leader>xx", "<cmd>Trouble diagnostics toggle<CR>", desc = "Diagnostics" },
      { "<leader>xX", "<cmd>Trouble diagnostics toggle filter.buf=0<CR>", desc = "Buffer diagnostics" },
    },
  },
  {
    "folke/todo-comments.nvim",
    event = { "BufReadPost", "BufNewFile" },
    dependencies = { "nvim-lua/plenary.nvim" },
    opts = {},
  },
}
''',

"lua/plugins/git-ui.lua": r'''return {
  {
    "lewis6991/gitsigns.nvim",
    event = { "BufReadPre", "BufNewFile" },
    opts = {
      on_attach = function(buf)
        local gs = package.loaded.gitsigns
        local function m(k, f, d)
          vim.keymap.set("n", k, f, { buffer = buf, desc = d })
        end
        m("]c", gs.next_hunk, "Next git hunk")
        m("[c", gs.prev_hunk, "Previous git hunk")
        m("<leader>gp", gs.preview_hunk, "Preview hunk")
        m("<leader>gb", gs.blame_line, "Blame line")
        m("<leader>gt", gs.toggle_current_line_blame, "Toggle blame")
      end,
    },
  },
  { "nvim-tree/nvim-web-devicons", lazy = true },
  {
    "nvim-lualine/lualine.nvim",
    event = "VeryLazy",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = { options = { theme = "auto", globalstatus = true } },
  },
  {
    "folke/flash.nvim",
    event = "VeryLazy",
    opts = {},
    keys = {
      { "s", mode = { "n", "x", "o" }, function() require("flash").jump() end, desc = "Flash" },
      { "S", mode = { "n", "x", "o" }, function() require("flash").treesitter() end, desc = "Flash Treesitter" },
    },
  },
}
''',
}

def remove_path_completely(path):
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)

def install_config(force=False):
    if CONFIG.exists() and any(CONFIG.iterdir()) and not (CONFIG / ".nvim-cpp-rhel9").exists():
        if not force:
            raise RuntimeError("~/.config/nvim already exists; rerun install with --fresh to permanently replace it")
        remove_path_completely(CONFIG)
    for rel, content in FILES.items():
        atomic_write(CONFIG / rel, content)
    atomic_write(CONFIG / ".nvim-cpp-rhel9", "managed=true\n")
    ok(f"Installed config in {CONFIG}")

def prepare_fresh_install():
    """Permanently delete all existing user-level Neovim files. No backup."""
    found = False
    for path in (CONFIG, DATA, CACHE, STATE, NVIM_ROOT, BIN / "nvim"):
        if path.exists() or path.is_symlink():
            remove_path_completely(path)
            ok(f"Deleted {path}")
            found = True
    if not found:
        ok("No existing user-level Neovim setup found")

def install_search_tools():
    missing = [x for x in ("rg", "fd") if not cmd(x)]
    if not missing:
        ok("ripgrep and fd found")
        return
    cargo = cmd("cargo")
    if not cargo:
        warn("ripgrep/fd missing and cargo unavailable; Telescope remains usable with reduced search features")
        return
    crates = {"rg": "ripgrep", "fd": "fd-find"}
    for name in missing:
        info(f"Installing {crates[name]} with cargo under ~/.local")
        p = run([cargo, "install", "--locked", "--root", LOCAL, crates[name]], check=False)
        if p.returncode: warn(f"Could not install {crates[name]}")

def bootstrap(update=False):
    nvim = cmd("nvim")
    env = os.environ.copy()
    env["PATH"] = f"{BIN}:{env.get('PATH','')}"
    actions = ["+Lazy! update" if update else "+Lazy! sync", "+MasonToolsInstallSync", "+TSUpdateSync", "+qa"]
    info("Bootstrapping plugins, optional missing C++ tools, and parsers")
    p = run([nvim, "--headless", *actions], check=False, capture=True, env=env)
    if p.returncode:
        warn("Headless bootstrap had errors; open nvim and run :Lazy sync then :MasonToolsInstall")
        print(p.stdout or "")
    else:
        ok("Plugin bootstrap completed")

def version(name, args=("--version",)):
    path = cmd(name)
    if not path: return False, "not found"
    p = run([path, *args], check=False, capture=True)
    lines = (p.stdout or "").strip().splitlines()
    return p.returncode == 0, lines[0] if lines else path

def doctor():
    print("\nNeovim C++ environment doctor\n")
    required = {"nvim", "git", "clangd", "clang-format"}
    checks = [
        ("nvim", ("--version",)), ("git", ("--version",)),
        ("clangd", ("--version",)), ("clang-format", ("--version",)),
        ("cmake", ("--version",)), ("clang", ("--version",)),
        ("gcc", ("--version",)), ("g++", ("--version",)),
        ("gdb", ("--version",)), ("rg", ("--version",)),
        ("fd", ("--version",)), ("make", ("--version",)),
        ("gdev", ("--help",)),
    ]
    errors = 0
    for name, args in checks:
        found, text = version(name, args)
        if found: ok(f"{name:<14} {text}")
        elif name in required:
            fail(f"{name:<14} {text}"); errors += 1
        else: warn(f"{name:<14} {text}")
    path_parts = os.environ.get("PATH", "").split(":")
    if str(BIN) in path_parts: ok(f"PATH includes {BIN}")
    else: warn(f"PATH missing {BIN}; run: source ~/.bashrc")
    if CONFIG.exists(): ok(f"Config exists: {CONFIG}")
    else: fail(f"Config missing: {CONFIG}"); errors += 1
    return 1 if errors else 0

def install(force=False, fresh=False, skip_search=False):
    for p in (BIN, LOG.parent): p.mkdir(parents=True, exist_ok=True)
    missing = [x for x in ("git", "tar") if not cmd(x)]
    if missing: raise RuntimeError("Required commands missing: " + ", ".join(missing))
    if fresh:
        prepare_fresh_install()
    ver = install_neovim()
    update_bashrc()
    install_config(force or fresh)
    if not skip_search: install_search_tools()
    bootstrap(False)
    ok(f"Ready: {ver}")
    print("Run: source ~/.bashrc && nvim")

def update(skip_search=False):
    ver = install_neovim()
    update_bashrc()
    if not CONFIG.exists(): install_config(False)
    if not skip_search: install_search_tools()
    bootstrap(True)
    ok(f"Updated environment: {ver}")

def clean():
    for p in (CACHE, STATE):
        if p.exists(): shutil.rmtree(p); ok(f"Removed {p}")

def remove_path():
    if not BASHRC.exists(): return
    text = BASHRC.read_text(encoding="utf-8")
    if BEGIN in text and END in text:
        before = text.split(BEGIN, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip("\n")
        atomic_write(BASHRC, before + (("\n\n" + after) if after else "\n"))
        ok("Removed PATH block from ~/.bashrc")

def uninstall(keep_config=False, keep_data=False):
    targets = [NVIM_ROOT, BIN / "nvim"]
    if not keep_config: targets.append(CONFIG)
    if not keep_data: targets += [DATA, CACHE, STATE]
    for p in targets:
        if p.is_symlink() or p.is_file(): p.unlink(missing_ok=True); ok(f"Removed {p}")
        elif p.exists(): shutil.rmtree(p); ok(f"Removed {p}")
    remove_path()

def main():
    ap = argparse.ArgumentParser(description="User-local Neovim C++ setup for RHEL 9")
    sp = ap.add_subparsers(dest="action", required=True)
    i = sp.add_parser("install")
    mode = i.add_mutually_exclusive_group()
    mode.add_argument("--force", action="store_true", help="Replace an unmanaged config without backing it up")
    mode.add_argument("--fresh", action="store_true", help="Permanently delete all user-level Neovim files and install clean")
    i.add_argument("--skip-search-tools", action="store_true")
    u = sp.add_parser("update")
    u.add_argument("--skip-search-tools", action="store_true")
    sp.add_parser("doctor")
    sp.add_parser("clean")
    x = sp.add_parser("uninstall")
    x.add_argument("--keep-config", action="store_true")
    x.add_argument("--keep-data", action="store_true")
    a = ap.parse_args()
    try:
        if a.action == "install": install(a.force, a.fresh, a.skip_search_tools)
        elif a.action == "update": update(a.skip_search_tools)
        elif a.action == "doctor": return doctor()
        elif a.action == "clean": clean()
        elif a.action == "uninstall": uninstall(a.keep_config, a.keep_data)
        return 0
    except KeyboardInterrupt:
        fail("Interrupted"); return 130
    except Exception as e:
        fail(str(e)); fail(f"Log: {LOG}"); return 1

if __name__ == "__main__":
    raise SystemExit(main())
