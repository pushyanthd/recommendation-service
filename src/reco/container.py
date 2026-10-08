"""Read-only container application with an explicit local snapshot mount."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI

from reco.api import create_app


def application() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return create_app(Path(os.environ.get("RECO_BUNDLE_ROOT", "/opt/models")))
