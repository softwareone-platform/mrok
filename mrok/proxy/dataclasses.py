from __future__ import annotations

from dataclasses import dataclass

from mrok.http.types import StreamReader, StreamWriter


@dataclass
class CachedStreamEntry:
    reader: StreamReader
    writer: StreamWriter
    last_access: float
