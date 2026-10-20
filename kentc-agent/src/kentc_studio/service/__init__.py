"""Studio services: cases, their documents, and the jobs that process them."""

from .cases import CaseService

Studio = CaseService

__all__ = ["CaseService", "Studio"]
