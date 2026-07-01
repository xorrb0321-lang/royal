"""Best-practice Instagram login with session reuse and UUID preservation."""

from __future__ import annotations

import logging
from typing import Callable

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from auth.challenge_handler import attach_handlers
from auth.session_manager import SessionManager
from config import InstagramConfig, load_config

logger = logging.getLogger(__name__)


def _apply_client_config(client: Client, config: InstagramConfig) -> None:
    if config.proxy:
        client.set_proxy(config.proxy)
        logger.info("Applied proxy for account %s", config.username)

    client.set_country(config.country)
    client.set_locale(config.locale)
    client.timezone_offset = config.timezone_offset


def _validate_session(client: Client) -> None:
    client.get_timeline_feed()


def _relogin_preserve_device(client: Client, config: InstagramConfig) -> None:
    old_settings = client.get_settings()
    client.set_settings({})
    if old_settings.get("uuids"):
        client.set_uuids(old_settings["uuids"])
    client.login(config.username, config.password)


def login_user(
    config: InstagramConfig | None = None,
    session_manager: SessionManager | None = None,
    prompt_fn: Callable[[str], str] | None = None,
) -> Client:
    """
    Log in using saved session settings when available.

    Falls back to password login while preserving device UUIDs on relogin.
    """
    config = config or load_config()
    session_manager = session_manager or SessionManager.from_config(config)

    client = Client()
    _apply_client_config(client, config)
    attach_handlers(client, totp_secret=config.totp_secret, prompt_fn=prompt_fn)

    login_via_session = False
    login_via_password = False

    if session_manager.has_saved_session():
        try:
            session_manager.load_into_client(client)
            client.login(config.username, config.password)
            try:
                _validate_session(client)
            except LoginRequired:
                logger.info("Saved session expired; relogin with same device UUIDs")
                _relogin_preserve_device(client, config)
            login_via_session = True
        except Exception as exc:
            logger.warning("Session login failed: %s", exc)

    if not login_via_session:
        logger.info("Attempting fresh login for %s", config.username)
        client.login(config.username, config.password)
        login_via_password = True

    if not login_via_session and not login_via_password:
        raise RuntimeError("Could not log in with saved session or password")

    session_manager.save_from_client(client)
    logger.info("Login successful for %s", config.username)
    return client


def get_client(
    config: InstagramConfig | None = None,
    prompt_fn: Callable[[str], str] | None = None,
) -> Client:
    """Convenience wrapper that returns an authenticated instagrapi Client."""
    return login_user(config=config, prompt_fn=prompt_fn)


def login_by_sessionid(sessionid: str, config: InstagramConfig | None = None) -> Client:
    """
    Log in using a browser sessionid.

    This is a lightweight compatibility path and is less stable than
    dump_settings/load_settings based session reuse.
    """
    config = config or load_config()
    client = Client()
    _apply_client_config(client, config)
    client.login_by_sessionid(sessionid)
    return client
