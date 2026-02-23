"""Edit file tool."""

from __future__ import annotations

import json
import os

EDIT_TOOL = {
    "type": "function",
    "function": {
        "name": "edit",
        "description": (
            "Edit a file by replacing a specific string with a new string. "
            "The oldString must be unique in the file to avoid ambiguous replacements. "
            "Use the read tool first to understand the file content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "The path to the file to edit.",
                },
                "oldString": {
                    "type": "string",
                    "description": (
                        "The exact string to replace. Must be unique in the file. "
                        "Include enough context to make it unique."
                    ),
                },
                "newString": {
                    "type": "string",
                    "description": "The new string to replace the old string with.",
                },
                "replaceAll": {
                    "type": "boolean",
                    "description": (
                        "If true, replace all occurrences. "
                        "Default is false (replace first occurrence only)."
                    ),
                },
            },
            "required": ["filePath", "oldString", "newString"],
        },
    },
}


def execute_edit(args: dict) -> str:
    """Execute the edit tool and return a JSON string."""
    file_path: str = args["filePath"]
    old_string: str = args["oldString"]
    new_string: str = args["newString"]
    replace_all: bool = args.get("replaceAll", False)

    try:
        abs_path = os.path.abspath(file_path)
        with open(abs_path, encoding="utf-8") as f:
            content = f.read()

        occurrences = content.count(old_string)

        if occurrences == 0:
            return json.dumps({
                "success": False,
                "error": "The specified string was not found in the file.",
            })

        if occurrences > 1 and not replace_all:
            return json.dumps({
                "success": False,
                "error": (
                    f"The string appears {occurrences} times in the file. "
                    "Either provide more context to make it unique, "
                    "or set replaceAll to true."
                ),
                "occurrences": occurrences,
            })

        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return json.dumps({
            "success": True,
            "path": abs_path,
            "replacements": occurrences if replace_all else 1,
            "message": (
                f"Successfully replaced {occurrences if replace_all else 1} occurrence(s)"
            ),
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Failed to edit file: {exc}"})
