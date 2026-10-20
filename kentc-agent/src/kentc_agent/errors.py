"""Exceptions shared by the core and the application layers."""

from __future__ import annotations


class Aborted(Exception):
    """The user interrupted the run (Ctrl-C); the context was left consistent."""


class ToolError(Exception):
    """A failure reported back to the model as the tool's result."""
