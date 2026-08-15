"""Challenge and 2FA handlers for instagrapi login flows."""

from __future__ import annotations

import logging
from typing import Callable

from instagrapi.mixins.challenge import ChallengeChoice

logger = logging.getLogger(__name__)


def build_challenge_code_handler(
    prompt_fn: Callable[[str], str] | None = None,
) -> Callable[[str, ChallengeChoice], str]:
    """Return a handler that collects SMS/email verification codes."""

    def _prompt(message: str) -> str:
        if prompt_fn is not None:
            return prompt_fn(message).strip()
        return input(message).strip()

    def challenge_code_handler(username: str, choice: ChallengeChoice) -> str:
        channel = "SMS" if choice == ChallengeChoice.SMS else "EMAIL"
        logger.info("Challenge required for %s via %s", username, channel)
        code = _prompt(f"[{username}] Enter {channel} verification code: ")
        if not code:
            raise ValueError("Verification code cannot be empty")
        return code

    return challenge_code_handler


def build_totp_handler(totp_secret: str) -> Callable[[], str]:
    """Return a TOTP code generator for accounts with authenticator 2FA."""

    try:
        import pyotp
    except ImportError as exc:
        raise ImportError(
            "pyotp is required for TOTP 2FA. Install with: pip install pyotp"
        ) from exc

    totp = pyotp.TOTP(totp_secret)

    def totp_handler() -> str:
        return totp.now()

    return totp_handler


def attach_handlers(
    client,
    *,
    totp_secret: str | None = None,
    prompt_fn: Callable[[str], str] | None = None,
) -> None:
    """Attach challenge handlers to an instagrapi Client."""
    client.challenge_code_handler = build_challenge_code_handler(prompt_fn)

    if totp_secret:
        client.totp_handler = build_totp_handler(totp_secret)
