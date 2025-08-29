import asyncio
import logging

import typer

from app.conf import Settings
from app.db.base import session_factory
from app.db.handlers import AccountHandler, EntitlementHandler
from app.db.models import Account
from app.enums import AccountStatus, EntitlementStatus
from app.telemetry import capture_telemetry_cli_command

BATCH_SIZE = 100


logger = logging.getLogger(__name__)



def command(ctx: typer.Context):
    pass
    # asyncio.run()