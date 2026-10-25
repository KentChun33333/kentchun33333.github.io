"""Skills: Markdown files that tell an agent how to do a kind of work (`<library>/<name>.md`).

A skill is prose only: what to look for, how to judge, how to write. An optional YAML front matter
(`---` / `description: ...` / `---`) documents it for people and is not given to the model. The body goes into the
agent's system prompt verbatim, as `## Skill: <name>`; it is not a template.
"""

from __future__ import annotations

import re
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONT_RE = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.DOTALL)


class SkillError(ValueError):
    pass


def skill_text(library: Path, name: str) -> str:
    """The body of one skill; SkillError when the name is malformed, the file is missing or the body is empty."""
    if not NAME_RE.match(name):
        raise SkillError(f"skill {name!r}: use lower-case words joined by -, e.g. document-extraction")
    path = library / f"{name}.md"
    if not path.is_file():
        raise SkillError(f"skill {name!r}: {path} not found")
    body = FRONT_RE.sub("", path.read_text(encoding="utf-8"), count=1).strip()
    if not body:
        raise SkillError(f"skill {name!r}: {path.name} is empty")
    return body


def load_skills(library: Path, names: list[str]) -> str:
    """The skills, in the given order (a repeated name once), as one system-prompt section."""
    if not names:
        raise SkillError("needs at least one skill")
    seen = list(dict.fromkeys(names))
    return "\n\n".join(f"## Skill: {n}\n\n{skill_text(library, n)}" for n in seen)
