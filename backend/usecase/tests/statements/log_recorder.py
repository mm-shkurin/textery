"""Collecting one named logger's records for the duration of one test.

1.2 grew this as a private handler class plus three lines of attach/detach
bookkeeping inside `AiEditRefusalLogStatements`; 1.3 needs the same thing on its
own logger, and one of its tests needs it on *both* loggers at once to compare the
two guards' record shapes. Three copies of "add a handler, force INFO, remember to
put the level back" is three chances to leave a process-global `setLevel` behind
for every later test in the run, which is a failure that shows up somewhere else.
"""

import logging


class _RecordingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class RecordingLogger:
    """Attach to one logger by name, collect its records, and undo both mutations.

    `stop()` restores the previous level as well as removing the handler: removing
    the handler alone would leave a permanent `setLevel(INFO)` on a module logger
    that every later test in the process shares.
    """

    def __init__(self, logger_name: str) -> None:
        self.logger_name = logger_name
        self._handler = _RecordingHandler()
        self._logger = logging.getLogger(logger_name)
        self._previous_level: int | None = None

    def start(self) -> None:
        self._previous_level = self._logger.level
        self._logger.addHandler(self._handler)
        self._logger.setLevel(logging.INFO)

    def stop(self) -> None:
        self._logger.removeHandler(self._handler)
        if self._previous_level is not None:
            self._logger.setLevel(self._previous_level)
        self._handler.close()

    def clear(self) -> None:
        self._handler.records.clear()

    def taken(self) -> list[logging.LogRecord]:
        """Hand back what was collected since the last `clear()`, as a snapshot."""
        return list(self._handler.records)
