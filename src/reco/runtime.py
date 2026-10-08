"""Private entrypoint for a CLI-owned process (ownership token is never an API input)."""

import argparse
import logging
from pathlib import Path

import uvicorn

from reco.api import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(create_app(args.root), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
