import pytest

from mrok.frontend.utils import parse_accept_header


@pytest.mark.parametrize(
    ("accept_header", "expected"),
    [
        ("text/html, application/json", ["text/html", "application/json"]),
        ("text/html;q=0.8, application/json;q=0.9", ["application/json", "text/html"]),
        (
            "text/plain;q=0.1, text/html, application/json;q=0.5",
            ["text/html", "application/json", "text/plain"],
        ),
        (
            "application/json;q=0.7, text/html;q=0.7, text/plain;q=0.7",
            ["application/json", "text/html", "text/plain"],
        ),
        ("*/*;q=0.1, application/json, text/*;q=0.5", ["application/json", "text/*", "*/*"]),
        (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,application/json;q=0.8",
            [
                "text/html",
                "application/xhtml+xml",
                "image/webp",
                "application/xml",
                "application/json",
            ],
        ),
        ("application/json, text/html;q=0", ["application/json", "text/html"]),
        (None, ["*/*"]),
        ("", ["*/*"]),
    ],
)
def test_parse_accept_header(accept_header: str | None, expected: list[str]):
    assert parse_accept_header(accept_header) == expected


def test_wrong_accept_string():
    assert parse_accept_header(",") == []


def test_wrong_weight():
    assert parse_accept_header(
        "text/html;q=0.8, application/json;q=0.9, application/xml;q=1a4"
    ) == ["application/json", "text/html", "application/xml"]
