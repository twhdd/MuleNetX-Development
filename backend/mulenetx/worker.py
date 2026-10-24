"""Worker entrypoint (SRS §4.4, §7.8): claims and executes jobs from the PostgreSQL queue."""

from __future__ import annotations

import logging
import signal
import sys
from types import FrameType

from mulenetx.core.config import get_settings
from mulenetx.core.logging import configure_logging
from mulenetx.core.runtime import Runtime
from mulenetx.db.schema_version import code_head, schema_matches
from mulenetx.jobs.handlers import build_handlers
from mulenetx.jobs.runner import Runner

logger = logging.getLogger("mulenetx.worker")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    runtime = Runtime(settings)
    if not schema_matches(runtime.engine):
        logger.error("schema version does not match code head %s; refusing to start", code_head())
        return 1
    runner = Runner(runtime, build_handlers())

    def _stop(signum: int, frame: FrameType | None) -> None:
        logger.info("stop signal received")
        runner.stopping.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        runner.run_forever()
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
