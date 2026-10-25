"""Declared checks on a JSON answer, beyond its shape: deterministic rules the answer must pass before it is kept.

    checks:                                   # path -> rule, or path -> [rules]
      title: required                         # present and not empty
      key_risks: min 1                        # a list's item count (or a string's length): min N / max N
      key_risks[].score: 0..100               # a number in an inclusive range
      reference: match INV-[0-9]+             # the whole string matches the regex

A path walks objects with `.` and every item of a list with `[]`. `parse_checks` validates rules against the
answer's shape when an agent is loaded; `check_rules` lists what an answer breaks ([] when it passes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

RANGE_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)$")
COUNT_RE = re.compile(r"^(min|max)\s+(\d+)$")
MISSING = object()


@dataclass(frozen=True)
class Rule:
    path: str
    kind: str                       # required | range | min | max | match
    low: float = 0
    high: float = 0
    pattern: re.Pattern[str] | None = None
    text: str = ""                  # the rule as written, for messages


def _parse_rule(path: str, text: str) -> Rule:
    t = str(text).strip()
    if t == "required":
        return Rule(path, "required", text=t)
    if m := RANGE_RE.match(t):
        low, high = float(m[1]), float(m[2])
        if low > high:
            raise ValueError(f"{path}: {t}: the range runs low..high")
        return Rule(path, "range", low, high, text=t)
    if m := COUNT_RE.match(t):
        return Rule(path, m[1], float(m[2]), text=t)
    if t.startswith("match "):
        try:
            return Rule(path, "match", pattern=re.compile(t[6:].strip()), text=t)
        except re.error as e:
            raise ValueError(f"{path}: {t}: bad regex ({e})") from None
    raise ValueError(f"{path}: unknown rule {t!r} (required | A..B | min N | max N | match REGEX)")


def _shape_at(shape: Any, path: str) -> Any:
    for part in path.split("."):
        many = part.endswith("[]")
        key = part[:-2] if many else part
        if not isinstance(shape, dict) or key not in shape:
            return MISSING
        shape = shape[key]
        if many:
            if not isinstance(shape, list) or not shape:
                return MISSING
            shape = shape[0]
    return shape


def parse_checks(checks: dict[str, Any] | None, shape: dict[str, Any]) -> list[Rule]:
    """The rules of a `checks` mapping; ValueError names the first path or rule that cannot apply to `shape`."""
    rules: list[Rule] = []
    for path, given in (checks or {}).items():
        at = _shape_at(shape, str(path))
        if at is MISSING:
            raise ValueError(f"{path}: not in the output (walk lists with [], e.g. key_values[].location)")
        for text in given if isinstance(given, list) else [given]:
            rule = _parse_rule(str(path), text)
            if rule.kind == "range" and not (at in ("number", "integer") or isinstance(at, int | float)
                                             and not isinstance(at, bool)):
                raise ValueError(f"{path}: {rule.text}: a range needs a number in the output")
            if rule.kind in ("min", "max") and not isinstance(at, list | str):
                raise ValueError(f"{path}: {rule.text}: min / max need a list or a string in the output")
            if rule.kind == "match" and not isinstance(at, str):
                raise ValueError(f"{path}: {rule.text}: match needs a string in the output")
            rules.append(rule)
    return rules


def _values(data: Any, path: str) -> list[tuple[str, Any]]:
    """(concrete path, value) for every value the path reaches; a missing key yields MISSING."""
    out: list[tuple[str, Any]] = [("", data)]
    for part in path.split("."):
        many = part.endswith("[]")
        key = part[:-2] if many else part
        nxt: list[tuple[str, Any]] = []
        for where, value in out:
            here = f"{where}.{key}" if where else key
            value = value.get(key, MISSING) if isinstance(value, dict) else MISSING
            if many and isinstance(value, list):
                nxt += [(f"{here}[{i}]", item) for i, item in enumerate(value)]
            elif not many:
                nxt.append((here, value))
        out = nxt
    return out


def _broken(rule: Rule, value: Any) -> str | None:
    if rule.kind == "required":
        empty = value is MISSING or value is None or (isinstance(value, str | list | dict) and not
                                                     (value.strip() if isinstance(value, str) else value))
        return "is required (empty)" if empty else None
    if value is MISSING or value is None:
        return None                                  # the shape check reports missing keys
    if rule.kind == "range":
        ok = isinstance(value, int | float) and not isinstance(value, bool) and rule.low <= value <= rule.high
        return None if ok else f"must be within {rule.text}, got {value!r}"
    if rule.kind in ("min", "max"):
        if not isinstance(value, list | str):
            return None
        n, what = len(value), "items" if isinstance(value, list) else "characters"
        ok = n >= rule.low if rule.kind == "min" else n <= rule.low
        return None if ok else f"needs {rule.kind} {int(rule.low)} {what}, has {n}"
    if rule.kind == "match":
        ok = isinstance(value, str) and rule.pattern is not None and rule.pattern.fullmatch(value.strip())
        return None if ok else f"must match {rule.pattern.pattern if rule.pattern else ''}, got {value!r}"
    return None


def check_rules(data: Any, rules: list[Rule]) -> list[str]:
    """What `data` breaks, one message per value: `'key_values[2].location' is required (empty)`."""
    errors = []
    for rule in rules:
        for where, value in _values(data, rule.path):
            problem = _broken(rule, value)
            if problem:
                errors.append(f"{where!r} {problem}")
    return errors
