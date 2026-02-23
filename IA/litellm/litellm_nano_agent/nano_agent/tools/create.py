"""Create file tool."""

from __future__ import annotations

import json
import os

CREATE_TOOL = {
    "type": "function",
    "function": {
        "name": "create",
        "description": (
            "Create a new file with the specified content. "
            "The directory will be created if it does not already exist. "
            "By default, the tool refuses to overwrite an existing file; "
            "set overwrite to true to replace it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "The path (absolute or relative) of the file to create.",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write into the file.",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": (
                        "If true, overwrite the file when it already exists. "
                        "Default is false."
                    ),
                },
            },
            "required": ["filePath", "content"],
        },
    },
}


def execute_create(args: dict) -> str:
    """Execute the create tool and return a JSON string."""
    file_path: str = args["filePath"]
    content: str = args["content"]
    overwrite: bool = args.get("overwrite", False)

    try:
        abs_path = os.path.abspath(file_path)

        if os.path.exists(abs_path) and not overwrite:
            return json.dumps({
                "success": False,
                "error": (
                    f"File already exists: {abs_path}. "
                    "Set overwrite to true to replace it, "
                    "or use the edit tool to modify it."
                ),
            })

        # Create parent directories if needed
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

        return json.dumps({
            "success": True,
            "path": abs_path,
            "lines": line_count,
            "bytes": len(content.encode("utf-8")),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Failed to create file: {exc}"})
