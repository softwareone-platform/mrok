import pytest

from mrok.agent.devtools.inspector.utils import (
    CONTENT_TYPE_TO_LANGUAGE,
    build_tree,
    get_highlighter_language_by_content_type,
    hexdump,
    humanize_bytes,
    parse_content_type,
    parse_form_data,
)


@pytest.mark.parametrize(
    ("content_type_string", "expected"),
    [
        ("application/json", ("application/json", "utf-8", None)),
        ("application/json; charset=latin1", ("application/json", "latin1", None)),
        (
            "multipart/form-data; boundary=---my-boundary",
            ("multipart/form-data", None, "---my-boundary"),
        ),
        ("application/json; invalid", ("application/json", "utf-8", None)),
        ("application/octet-stream; invalid", ("application/octet-stream", None, None)),
        ("application/octet-stream; other=whatever", ("application/octet-stream", None, None)),
        ("text/plain; other=whatever", ("text/plain", "utf-8", None)),
    ],
)
def test_parse_content_type(content_type_string: str, expected: tuple[str, str | None, str | None]):
    content_type_info = parse_content_type(content_type_string)
    assert content_type_info.content_type == expected[0]
    assert content_type_info.charset == expected[1]
    assert content_type_info.boundary == expected[2]


def test_parse_form_data(multipart_body: tuple[str, bytes]):
    boundary, body = multipart_body

    result = list(parse_form_data(body, boundary))

    assert len(result) == 4
    assert result[0] == ("username", "john_doe")
    assert result[1] == ("email", "john@example.com")
    assert result[2] == ("message", "Hello, this is a test message!")
    assert result[3] == ("file", "<binary>")


def test_build_tree():
    class FakeNode:
        def __init__(self, data):
            self.data = data
            self.children = []

        def add(self, data):
            child = FakeNode(data)
            self.children.append(child)
            return child

    def dump_node(node):
        return (
            node.data,
            [dump_node(child) for child in node.children],
        )

    data = {
        "a": 1,
        "b": [2, {"c": 3}],
    }
    root = FakeNode("root")
    build_tree(root, data)

    assert dump_node(root) == (
        "root",
        [
            ("a", [("1", [])]),
            (
                "b",
                [
                    ("[0]", [("2", [])]),
                    ("[1]", [("c", [("3", [])])]),
                ],
            ),
        ],
    )


def test_hexdump():
    data = b"Hello World"
    result = hexdump(data, width=16)
    assert "48 65 6c 6c 6f 20 57 6f 72 6c 64" in result
    assert "Hello World" in result


def test_hexdump_non_printable():
    data = b"\x00\x01\x02ABC"
    result = hexdump(data)
    assert "00 01 02 41 42 43" in result
    assert "...ABC" in result


def test_hexdump_custom_width():
    data = b"123456"
    result = hexdump(data, width=3)
    lines = result.split("\n")
    assert len(lines) == 2
    assert lines[0].strip().endswith("123")
    assert lines[1].strip().endswith("456")


def test_hexdump_empty_input():
    assert hexdump(b"") == ""


@pytest.mark.parametrize(
    ("input_bytes", "expected_hex"),
    [
        (b"\xff", "ff"),
        (b"\x00", "00"),
        (b"\x20", "20"),
    ],
)
def test_hexdump_single_bytes(input_bytes, expected_hex):
    assert expected_hex in hexdump(input_bytes)


@pytest.mark.parametrize(
    ("input_bytes", "expected_value", "expected_unit"),
    [
        (0, 0.0, "B"),
        (1, 1.0, "B"),
        (999, 999.0, "B"),
        (1000, 1000.0, "B"),
        (1023, 1023.0, "B"),
        (1024, 1.0, "KiB"),
        (1025, 1.0, "KiB"),
        (1536, 1.5, "KiB"),
        (2047, 2.0, "KiB"),
        (5242880, 5.0, "MiB"),
        (1024**3 - 1, 1023.99, "MiB"),
        (1024**3, 1.0, "GiB"),
        (1024**4, 1.0, "TiB"),
        (1024**5, 1.0, "PiB"),
        (1024**6, 1024.0, "PiB"),
        (99_999_999_999_999, 90.95, "TiB"),
        (1_099_511_627_776, 1.0, "TiB"),
    ],
)
def test_humanize_bytes(input_bytes, expected_value, expected_unit):
    value, unit = humanize_bytes(input_bytes)
    assert value == pytest.approx(expected_value, abs=0.01)
    assert unit == expected_unit


def test_humanize_bytes_negative_value():
    with pytest.raises(ValueError, match="num_bytes must be non-negative"):
        humanize_bytes(-1)


@pytest.mark.parametrize(
    ("content_type", "language"), list(CONTENT_TYPE_TO_LANGUAGE.items()) + [("invalid", None)]
)
def test_get_highlighter_language_by_content_type(content_type: str, language: str):
    assert get_highlighter_language_by_content_type(content_type) == language
