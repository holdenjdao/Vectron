"""Language-neutral value types used in system specs.

Specs describe message fields and config parameters with a small type
vocabulary rather than Python types, so the same spec can later drive other
code targets (C++, Rust). Every literal value that ends up in generated code is
coerced through :func:`coerce` first, which is what makes it safe to render
spec values (including LLM-proposed ones) into source code.
"""

from __future__ import annotations

import math
from typing import Any, Literal, get_args

FieldType = Literal["float", "int", "bool", "str", "bytes", "vec3", "float[]", "int[]", "str[]"]
ScalarType = Literal["float", "int", "bool", "str"]

FIELD_TYPES: tuple[str, ...] = get_args(FieldType)
SCALAR_TYPES: tuple[str, ...] = get_args(ScalarType)

MAX_STR_LEN = 2000
MAX_ARRAY_LEN = 256


class SpecValueError(ValueError):
    """Raised when a value does not match its declared spec type."""


def default_for(field_type: str) -> Any:
    """Zero value for a field type (used when a spec gives no default)."""
    return {
        "float": 0.0,
        "int": 0,
        "bool": False,
        "str": "",
        "bytes": b"",
        "vec3": (0.0, 0.0, 0.0),
        "float[]": (),
        "int[]": (),
        "str[]": (),
    }[field_type]


def coerce(field_type: str, value: Any) -> Any:
    """Validate ``value`` against ``field_type`` and return its canonical form.

    Raises :class:`ValueError` for anything that does not fit, so callers can
    surface a precise error instead of generating broken code.
    """
    if field_type == "float":
        return _float(value)
    if field_type == "int":
        return _int(value)
    if field_type == "bool":
        return _bool(value)
    if field_type == "str":
        return _str(value)
    if field_type == "bytes":
        if isinstance(value, bytes):
            return value
        return _str(value).encode("utf-8")
    if field_type == "vec3":
        items = _sequence(value)
        if len(items) != 3:
            raise SpecValueError(f"vec3 needs exactly 3 numbers, got {len(items)}")
        return tuple(_float(v) for v in items)
    if field_type == "float[]":
        return tuple(_float(v) for v in _sequence(value))
    if field_type == "int[]":
        return tuple(_int(v) for v in _sequence(value))
    if field_type == "str[]":
        return tuple(_str(v) for v in _sequence(value))
    raise SpecValueError(f"unknown field type {field_type!r}")


def _float(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise SpecValueError(f"expected a number, got {value!r}")
    try:
        result = float(value)
    except ValueError as exc:
        raise SpecValueError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(result):
        raise SpecValueError("number must be finite")
    return result


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise SpecValueError(f"expected an integer, got {value!r}")
    if isinstance(value, int):
        return value
    number = _float(value)
    if not number.is_integer():
        raise SpecValueError(f"expected an integer, got {value!r}")
    return int(number)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise SpecValueError(f"expected a boolean, got {value!r}")


def _str(value: Any) -> str:
    if not isinstance(value, str):
        raise SpecValueError(f"expected a string, got {value!r}")
    if len(value) > MAX_STR_LEN:
        raise SpecValueError(f"string longer than {MAX_STR_LEN} characters")
    return value


def _sequence(value: Any) -> tuple[Any, ...]:
    if not isinstance(value, list | tuple):
        raise SpecValueError(f"expected a list, got {value!r}")
    if len(value) > MAX_ARRAY_LEN:
        raise SpecValueError(f"list longer than {MAX_ARRAY_LEN} items")
    return tuple(value)
