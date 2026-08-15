"""CLI entry point for Instagram session login."""

from __future__ import annotations

import argparse
import logging
import sys

from auth.login import get_client, login_by_sessionid
from config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _cmd_login() -> int:
    config = load_config()
    client = get_client(config)
    user_id = client.user_id
    logger.info("Authenticated as user_id=%s", user_id)
    return 0


def _cmd_verify() -> int:
    config = load_config()
    client = get_client(config)
    feed = client.get_timeline_feed()
    logger.info("Session valid. Timeline items: %d", len(feed.get("feed_items", [])))
    return 0


def _cmd_sessionid(sessionid: str) -> int:
    config = load_config()
    client = login_by_sessionid(sessionid, config)
    logger.info("Authenticated via sessionid as user_id=%s", client.user_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Instagram mobile-PC session manager (instagrapi)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("login", help="Login and persist session settings")
    subparsers.add_parser("verify", help="Validate saved session")

    sessionid_parser = subparsers.add_parser(
        "sessionid",
        help="Login using browser sessionid (less stable)",
    )
    sessionid_parser.add_argument("value", help="Instagram sessionid cookie value")

    args = parser.parse_args(argv)

    try:
        if args.command == "login":
            return _cmd_login()
        if args.command == "verify":
            return _cmd_verify()
        if args.command == "sessionid":
            return _cmd_sessionid(args.value)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1
    except Exception as exc:
        logger.exception("Command failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
