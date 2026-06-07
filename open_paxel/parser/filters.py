from __future__ import annotations

import re

LOCAL_CMD_PATTERN = re.compile(
    r"^\s*(ls|pwd|cd|cat|head|tail|echo|which|type|dir|Get-ChildItem|Get-Content)\b",
    re.IGNORECASE,
)


def is_local_shell_command(command: str) -> bool:
    return bool(LOCAL_CMD_PATTERN.match(command.strip()))


def apply_filter_stats(
    *,
    local_commands_removed: int = 0,
    tool_only_turns_removed: int = 0,
) -> dict[str, int]:
    return {
        "local_commands_removed": local_commands_removed,
        "tool_only_turns_removed": tool_only_turns_removed,
    }
