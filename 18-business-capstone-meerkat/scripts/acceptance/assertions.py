from __future__ import annotations


class AcceptanceFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceFailure(message)
