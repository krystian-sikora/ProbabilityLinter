from dataclasses import dataclass


@dataclass
class LintError:
    message: str
    tag: str
    line: int
    col: int
    offset: int
    end_offset: int | None = None
    severity: str = "error"   # "error" | "warning" | "info"
