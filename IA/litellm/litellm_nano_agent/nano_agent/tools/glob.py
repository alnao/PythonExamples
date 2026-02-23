"""Glob tool – find files by pattern."""

from __future__ import annotations

import json
import os
from glob import glob as _glob

GLOB_TOOL = {
    "type": "function",
    "function": {
        "name": "glob",
        "description": (
            "Find files matching a glob pattern. "
            "Use this to discover files in a codebase, find specific file types, "
            "or explore directory structures."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": (
                        "Glob pattern to match files. Examples: "
                        "'**/*.ts' for all TypeScript files, "
                        "'src/**/*' for all files in src."
                    ),
                },
                "directory": {
                    "type": "string",
                    "description": "Base directory to search from. Defaults to current directory.",
                },
                "maxResults": {
                    "type": "integer",
                    "description": "Maximum number of files to return (default: 100).",
                },
            },
            "required": ["pattern"],
        },
    },
}

_IGNORE_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv"}


def execute_glob(args: dict) -> str:
    """Execute the glob tool and return a JSON string."""
    pattern: str = args["pattern"]
    directory: str = args.get("directory", ".")
    max_results: int = args.get("maxResults", 100)

    try:
        abs_dir = os.path.abspath(directory)
        raw_files = _glob(os.path.join(abs_dir, pattern), recursive=True)

        # Filter out directories and ignored paths
        files: list[str] = []
        for fp in sorted(raw_files):
            parts = fp.split(os.sep)
            if any(p in _IGNORE_DIRS for p in parts):
                continue
            if os.path.isfile(fp):
                files.append(os.path.relpath(fp, abs_dir))

        limited = files[:max_results]

        return json.dumps({
            "success": True,
            "pattern": pattern,
            "directory": abs_dir,
            "fileCount": len(files),
            "truncated": len(files) > max_results,
            "files": limited,
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Glob search failed: {exc}"})
