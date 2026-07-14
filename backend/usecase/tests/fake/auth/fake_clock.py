from datetime import datetime


class FakeClock:
    def __init__(self, fixed_now: datetime) -> None:
        self.fixed_now = fixed_now

    def now(self) -> datetime:
        return self.fixed_now
