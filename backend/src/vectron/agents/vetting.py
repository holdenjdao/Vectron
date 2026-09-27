"""Static vetting of LLM-written Python before it is accepted into a build.

Vectron never executes generated code on the server. Instead, code from a model
must pass these checks: an import allowlist (stdlib subset + the package core),
no dangerous builtins or introspection escapes, and an unchanged interface
contract (class name, topics). Anything else is rejected and the module falls
back to its stub.
"""

from __future__ import annotations

import ast

from vectron.domain.spec import ModuleSpec

ALLOWED_STDLIB = frozenset(
    {
        "__future__",
        "abc",
        "bisect",
        "cmath",
        "collections",
        "copy",
        "dataclasses",
        "decimal",
        "enum",
        "fractions",
        "functools",
        "heapq",
        "itertools",
        "math",
        "numbers",
        "operator",
        "statistics",
        "string",
        "struct",
        "textwrap",
        "typing",
    }
)
ALLOWED_CORE = frozenset({"bus", "geo", "messages", "module"})
FORBIDDEN_NAMES = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "delattr",
        "eval",
        "exec",
        "exit",
        "getattr",
        "globals",
        "help",
        "input",
        "locals",
        "memoryview",
        "open",
        "quit",
        "setattr",
        "vars",
    }
)
FORBIDDEN_ATTRS = frozenset(
    {
        "__bases__",
        "__builtins__",
        "__class__",
        "__closure__",
        "__code__",
        "__dict__",
        "__getattribute__",
        "__globals__",
        "__import__",
        "__loader__",
        "__mro__",
        "__spec__",
        "__subclasses__",
    }
)


class VettingError(ValueError):
    """Generated code violated a factory rule."""


def vet_module_source(source: str, module: ModuleSpec) -> None:
    tree = _parse(source, "module")
    _check_nodes(tree, allow_relative=True, package=None)
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    cls = classes.get(module.class_name)
    if cls is None:
        raise VettingError(f"class {module.class_name} is missing")
    if not any(isinstance(base, ast.Name) and base.id == "Module" for base in cls.bases):
        raise VettingError(f"{module.class_name} must subclass Module")
    if _class_constant(cls, "name") != module.id:
        raise VettingError(f"{module.class_name}.name must stay {module.id!r}")
    for attr, expected in (("subscribes", module.subscribes), ("publishes", module.publishes)):
        if _class_dict_keys(cls, attr) != set(expected):
            raise VettingError(
                f"{module.class_name}.{attr} must declare exactly {sorted(expected)}"
            )


def vet_test_source(source: str, package: str) -> None:
    tree = _parse(source, "test")
    _check_nodes(tree, allow_relative=False, package=package)
    if not any(
        isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in tree.body
    ):
        raise VettingError("test file defines no test functions")


def _parse(source: str, what: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        raise VettingError(f"{what} source does not parse: {exc}") from exc


def _check_nodes(tree: ast.Module, *, allow_relative: bool, package: str | None) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_absolute(alias.name, package)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                _check_absolute(node.module or "", package)
            elif not allow_relative or node.level != 2:
                raise VettingError("relative imports are only allowed as `from ..core.x import`")
            else:
                parts = (node.module or "").split(".")
                if parts[0] != "core" or (len(parts) > 1 and parts[1] not in ALLOWED_CORE):
                    raise VettingError(f"import from ..{node.module} is not allowed")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise VettingError(f"use of {node.id!r} is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            raise VettingError(f"access to {node.attr!r} is not allowed")


def _check_absolute(name: str, package: str | None) -> None:
    top = name.split(".")[0]
    if top in ALLOWED_STDLIB or name in ALLOWED_STDLIB:
        return
    if package is not None and top in (package, "pytest"):
        return
    raise VettingError(f"import of {name!r} is not allowed")


def _class_constant(cls: ast.ClassDef, attr: str) -> object:
    for node in cls.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == attr for t in node.targets
        ):
            return node.value.value if isinstance(node.value, ast.Constant) else None
    return None


def _class_dict_keys(cls: ast.ClassDef, attr: str) -> set[str]:
    for node in cls.body:
        value = None
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == attr for t in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = node.value if node.target.id == attr else None
        if isinstance(value, ast.Dict):
            keys = set()
            for key in value.keys:
                if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    raise VettingError(f"{attr} keys must be string literals")
                keys.add(key.value)
            return keys
    raise VettingError(f"{cls.name}.{attr} must be a dict literal")
