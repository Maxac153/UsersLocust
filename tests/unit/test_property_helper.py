import json

import pytest

from src.tests.__common.helpers.property_helper import PropertyHelper


@pytest.mark.parametrize("env, expected", [
    (None, []),
    ([], []),
    ("", []),
    (["a.json", "b.json"], ["a.json", "b.json"]),
    ("a.json, b.json", ["a.json", "b.json"]),
])
def test_env_paths(env, expected):
    assert PropertyHelper.env_paths(env) == expected


def test_merge_order_files_then_cli_then_env(tmp_path):
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"HOST": "file", "LOGIN": "file"}))
    credentials = tmp_path / "redis.json"
    credentials.write_text(json.dumps({"LOGIN": "secret"}))

    properties = PropertyHelper.read_properties(
        json.dumps({"HOST": "cli", "ENV": [str(credentials)]}),
        str(base),
    )

    assert properties["HOST"] == "cli"
    assert properties["LOGIN"] == "secret"
