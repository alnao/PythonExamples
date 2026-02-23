"""
Tool definitions for the coding agent.

Each tool is a dict with:
  - "function": JSON-schema for litellm/OpenAI function calling
  - "execute":  Python callable that runs the tool
"""

from .read import READ_TOOL, execute_read
from .edit import EDIT_TOOL, execute_edit
from .create import CREATE_TOOL, execute_create
from .grep import GREP_TOOL, execute_grep
from .glob import GLOB_TOOL, execute_glob

# Registry: tool-name → executor
TOOL_EXECUTORS = {
    "read":   execute_read,
    "edit":   execute_edit,
    "create": execute_create,
    "grep":   execute_grep,
    "glob":   execute_glob,
}

# List expected by litellm's `tools` parameter
TOOLS = [READ_TOOL, EDIT_TOOL, CREATE_TOOL, GREP_TOOL, GLOB_TOOL]
