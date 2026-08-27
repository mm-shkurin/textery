from pydantic import BaseModel, StrictInt


class SaveDocumentRequestDto(BaseModel):
    content: str
    # Optional with default None: a required title would 422 every current client
    # and autosave that saves content without a title. Plain str (not StrictStr) --
    # Pydantic v2 lax mode already rejects int/float/bool for a str field, so a
    # non-string title 422s without extra strictness. Scenario 3.1 forwards it to
    # SaveDocument.execute so the export filename can be derived from the title.
    title: str | None = None
    # StrictInt, not int: Pydantic v2's lax mode coerces "5" and 5.0 to 5, so a lax
    # `version: int` would silently ACCEPT two of the three shapes scenario 8.1
    # calls "non-integer". StrictInt also rejects JSON `true`, which would otherwise
    # arrive as 1 (bool subclasses int).
    version: StrictInt
