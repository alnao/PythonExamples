"""Grep tool – regex search across files."""

from __future__ import annotations

import json
import os
import re
from glob import glob

GREP_TOOL = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": (
            "Search for a pattern (regex) in files. "
            "Returns matching lines with file paths and line numbers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for.",
                },
                "directory": {
                    "type": "string",
                    "description": "Directory to search in. Defaults to current directory.",
                },
                "filePattern": {
                    "type": "string",
                    "description": (
                        "Glob pattern for files to search. "
                        "Example: '**/*.ts' for TypeScript files."
                    ),
                },
                "caseSensitive": {
                    "type": "boolean",
                    "description": "Whether the search is case sensitive (default: true).",
                },
                "maxResults": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50).",
                },
            },
            "required": ["pattern"],
        },
    },
}

_IGNORE_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv"}


def execute_grep(args: dict) -> str:
    """Execute the grep tool and return a JSON string."""
    pattern: str = args["pattern"]
    directory: str = args.get("directory", ".")
    file_pattern: str = args.get("filePattern", "**/*")
    case_sensitive: bool = args.get("caseSensitive", True)
    max_results: int = args.get("maxResults", 50)

    try:
        abs_dir = os.path.abspath(directory)
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        files = glob(os.path.join(abs_dir, file_pattern), recursive=True)
        results: list[dict] = []

        for filepath in sorted(files):
            if len(results) >= max_results:
                break
            # Skip ignored directories and non-files
            parts = filepath.split(os.sep)
            if any(p in _IGNORE_DIRS for p in parts):
                continue
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if len(results) >= max_results:
                            break
                        if regex.search(line):
                            results.append({
                                "file": os.path.relpath(filepath, abs_dir),
                                "line": i,
                                "content": line.strip(),
                            })
            except (OSError, UnicodeDecodeError):
                continue

        return json.dumps({
            "success": True,
            "pattern": pattern,
            "directory": abs_dir,
            "matchCount": len(results),
            "truncated": len(results) >= max_results,
            "matches": results,
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Search failed: {exc}"})
