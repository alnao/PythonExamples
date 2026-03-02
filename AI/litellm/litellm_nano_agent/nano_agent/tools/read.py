"""Read file tool."""

from __future__ import annotations

import json
import os

READ_TOOL = {
    "type": "function",
    "function": {
        "name": "read",
        "description": (
            "Read the contents of a file. "
            "Use this to examine file contents, understand code, or analyse text files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "The absolute or relative path to the file to read.",
                },
                "startLine": {
                    "type": "integer",
                    "description": "Optional starting line number (1-indexed).",
                },
                "endLine": {
                    "type": "integer",
                    "description": "Optional ending line number (1-indexed, inclusive).",
                },
            },
            "required": ["filePath"],
        },
    },
}


def execute_read(args: dict) -> str:
    """Execute the read tool and return a JSON string."""
    file_path: str = args["filePath"]
    start_line: int | None = args.get("startLine")
    end_line: int | None = args.get("endLine")

    try:
        abs_path = os.path.abspath(file_path)
        with open(abs_path, encoding="utf-8") as f:
            lines = f.readlines()

        if start_line is not None or end_line is not None:
            start = (start_line or 1) - 1
            end = end_line or len(lines)
            selected = lines[start:end]
            content = "".join(
                f"{start + i + 1}: {line}" for i, line in enumerate(selected)
            )
            return json.dumps({
                "success": True,
                "path": abs_path,
                "content": content,
                "totalLines": len(lines),
                "linesShown": f"{start + 1}-{min(end, len(lines))}",
            })

        content = "".join(f"{i + 1}: {line}" for i, line in enumerate(lines))
        return json.dumps({
            "success": True,
            "path": abs_path,
            "content": content,
            "totalLines": len(lines),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Failed to read file: {exc}"})
