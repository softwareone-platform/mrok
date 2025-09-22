from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.theme import Theme


class MrokHighlighter(ReprHighlighter):
    prefixes = ("EXT", "ext", "INS", "ins")
    highlights = ReprHighlighter.highlights + [
        rf"(?P<mrok_id>(?:{'|'.join(prefixes)})(?:-\d{{4}})*)"
    ]


def get_console(stderr: bool = False) -> Console:
    return Console(
        stderr=stderr,
        highlighter=MrokHighlighter(),
        theme=Theme({"repr.mrok_id": "bold light_salmon3"}),
    )
