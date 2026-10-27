
# All rights reserved.


import socket
import time

import heroku3
from pyrogram import filters

import config
from VenomX.core.mongo import pymongodb

from .logging import LOGGER

SUDOERS = filters.user()


HAPP = None
_boot_ = time.time()


def is_heroku():
    return "heroku" in socket.getfqdn()


XCB = [
    "/",
    "@",
    ".",
    "com",
    ":",
    "git",
    "heroku",
    "push",
    str(config.HEROKU_API_KEY),
    "https",
    str(config.HEROKU_APP_NAME),
    "HEAD",
    "main",
]


def dbb():
    global db
    db = {}
    LOGGER(__name__).info(f"Database Initialized.")


def sudo():
    """
    Load owner/sudo permissions without making MongoDB a hard startup dependency.
    If MongoDB is missing or unreachable, the bot continues with OWNER_ID only.
    """
    global SUDOERS
    OWNER = config.OWNER_ID or []

    # Owner IDs should always be authorized, even when MongoDB is disabled/down.
    for user_id in OWNER:
        SUDOERS.add(user_id)

    if not config.MONGO_DB_URI:
        LOGGER(__name__).info(
            "MongoDB URI not configured; running with owner permissions only."
        )
        LOGGER(__name__).info("Sudoers Loaded.")
        return

    try:
        sudoersdb = pymongodb.sudoers
        record = sudoersdb.find_one({"sudo": "sudo"})
        sudoers = list(record.get("sudoers", [])) if record else []

        # Keep configured owners in the persisted list when MongoDB is available.
        changed = False
        for user_id in OWNER:
            if user_id not in sudoers:
                sudoers.append(user_id)
                changed = True

        if changed or record is None:
            sudoersdb.update_one(
                {"sudo": "sudo"},
                {"$set": {"sudoers": sudoers}},
                upsert=True,
            )

        for user_id in sudoers:
            SUDOERS.add(user_id)

        LOGGER(__name__).info("Sudoers Loaded from MongoDB.")
    except Exception as exc:
        # Mongo is optional for boot: owner commands still work, DB-backed
        # features may be unavailable until the database reconnects.
        LOGGER(__name__).warning(
            "MongoDB unavailable while loading sudoers; continuing with "
            "OWNER_ID permissions only. Error: %s",
            exc,
        )
        LOGGER(__name__).info("Sudoers Loaded (MongoDB fallback).")


def heroku():
    global HAPP
    if is_heroku():
        if config.HEROKU_API_KEY and config.HEROKU_APP_NAME:
            try:
                Heroku = heroku3.from_key(config.HEROKU_API_KEY)
                HAPP = Heroku.app(config.HEROKU_APP_NAME)
                LOGGER(__name__).info(f"Heroku App Configured")
            except Exception:
                LOGGER(__name__).warning(
                    f"Please make sure your Heroku API Key and Your App name are configured correctly in the heroku."
                )
