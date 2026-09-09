"""Shared value objects.

Small, immutable types that carry a rule the rest of the codebase would otherwise
re-implement. They are plain Python — no Django import — so they stay trivially testable.
"""

from dataclasses import dataclass

__all__ = ["SecretString"]

MASK_CHARACTER = "•"
VISIBLE_SUFFIX_LENGTH = 4


@dataclass(frozen=True, slots=True)
class SecretString:
    """A credential that must never be rendered in full.

    ``str()`` and ``repr()`` both return the masked form, so a secret cannot leak through
    an f-string, a log record or a traceback by accident. The raw value is only reachable
    through the explicit :meth:`reveal` call.
    """

    value: str

    def reveal(self) -> str:
        """Return the raw credential. Call sites should be few and deliberate."""
        return self.value

    def masked(self) -> str:
        """Return the credential with everything but its last few characters hidden."""
        if not self.value:
            return ""
        if len(self.value) <= VISIBLE_SUFFIX_LENGTH:
            return MASK_CHARACTER * len(self.value)
        hidden_length = len(self.value) - VISIBLE_SUFFIX_LENGTH
        return MASK_CHARACTER * hidden_length + self.value[-VISIBLE_SUFFIX_LENGTH:]

    def __str__(self) -> str:
        return self.masked()

    def __repr__(self) -> str:
        return f"SecretString({self.masked()!r})"

    def __bool__(self) -> bool:
        return bool(self.value)
