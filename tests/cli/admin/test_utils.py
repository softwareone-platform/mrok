from mrok.cli.commands.admin.utils import extract_names, format_tags, format_timestamp


def test_format_tags():
    data = {"mrok": "v1.0.x", "build": "dev"}

    assert format_tags(data) == "mrok: v1.0.x\nbuild: dev"
    assert format_tags({}) == "-"


def test_extract_names():
    data = [
        {"id": "id1", "name": "First name"},
        {"id": "id2", "name": "Second name"},
        {"id": "id3", "last_name": "Third name"},
    ]

    assert extract_names(data) == "First name\nSecond name"
    assert extract_names([]) == "-"


def test_format_timestamp():
    date = "2025-08-26T14:26:53.332Z"

    assert format_timestamp(date) == "2025-08-26 14:26:53"
