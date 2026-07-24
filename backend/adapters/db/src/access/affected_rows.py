from typing import Any, cast

from sqlalchemy import CursorResult
from sqlalchemy.engine import Result


def affected_rows(result: Result[Any]) -> int:
    """How many rows a DML statement actually touched.

    `session.execute()` is typed as returning `Result`, which has no `rowcount` --
    only `CursorResult`, the subclass it genuinely returns for INSERT/UPDATE/
    DELETE, does. The narrowing lives here rather than being repeated at each
    call site, and it is the one place to look when asking why the cast is safe:
    it is, for DML, and it is not for a SELECT, which is why this function is
    named after the thing only DML has.
    """
    return cast(CursorResult[Any], result).rowcount
