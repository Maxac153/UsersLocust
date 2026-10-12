import argparse

TRUE_VALUES = frozenset({"true", "1", "yes", "y", "on"})
FALSE_VALUES = frozenset({"false", "0", "no", "n", "off"})


def str_to_bool(value: str | bool) -> bool:
    # bool("false") is True, so CLI/env flags must be parsed explicitly
    if isinstance(value, bool):
        return value

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise argparse.ArgumentTypeError(f"Expected Boolean Value, Got: {value!r}")


def bool_to_cli(value: bool) -> str:
    return "true" if value else "false"
