import argparse

import pytest

from src.tests.__common.helpers.cli_helper import bool_to_cli, str_to_bool


@pytest.mark.parametrize("raw", ["true", "TRUE", " True ", "1", "yes", "on"])
def test_str_to_bool_true_values(raw):
    assert str_to_bool(raw) is True


@pytest.mark.parametrize("raw", ["false", "FALSE", " False ", "0", "no", "off"])
def test_str_to_bool_false_values(raw):
    assert str_to_bool(raw) is False


def test_str_to_bool_passes_through_bool_default():
    assert str_to_bool(False) is False


def test_str_to_bool_rejects_garbage():
    with pytest.raises(argparse.ArgumentTypeError):
        str_to_bool("treu")


@pytest.mark.parametrize("value", [True, False])
def test_bool_to_cli_round_trip(value):
    assert str_to_bool(bool_to_cli(value)) is value
