# VS Code C++ Setup

## Extensions
- C/C++ (Microsoft)
- clangd (LLVM)
- CMake Tools
- GitLens (optional)
- Error Lens (optional)

## Use clangd
Disable Microsoft's IntelliSense:

```json
"C_Cpp.intelliSenseEngine": "disabled"
```

## compile_commands.json
Your project generates:

```
build/rhel9/Debug/compile_commands.json
```

From the project root:

```bash
ln -sfn "$PWD/build/rhel9/Debug/compile_commands.json" compile_commands.json
```

## Workspace settings
Create `.vscode/settings.json`:

```json
{
  "clangd.arguments": [
    "--background-index",
    "--clang-tidy"
  ]
}
```

## Build task
Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Build Debug",
      "type": "shell",
      "command": "x-full-build-debug",
      "group": {
        "kind": "build",
        "isDefault": true
      }
    },
    {
      "label": "Build",
      "type": "shell",
      "command": "x-full-build"
    }
  ]
}
```

Run the default build with **Ctrl+Shift+B**.

## Recommended settings
- Enable format on save if using clang-format.
- Open the project root, not the build directory.
- Ensure `clangd`, `cmake`, and your compiler are on PATH.

## Troubleshooting
- Run `clangd --version`.
- Verify `compile_commands.json` exists.
- Reload the VS Code window after building if IntelliSense looks stale.
