from __future__ import annotations

import pytest

from vectron.agents.vetting import VettingError, vet_module_source, vet_test_source
from vectron.domain.spec import ModuleSpec

MODULE = ModuleSpec(
    id="echo",
    name="Echo",
    responsibility="Echo pings.",
    subscribes=["io.ping_in"],
    publishes=["io.ping_out"],
)

GOOD = """
import math
from ..core.messages import Ping
from ..core.module import Module

class Echo(Module):
    name = "echo"
    subscribes = {"io.ping_in": Ping}
    publishes = {"io.ping_out": Ping}
"""


def test_good_module_passes() -> None:
    vet_module_source(GOOD, MODULE)


@pytest.mark.parametrize(
    ("snippet", "reason"),
    [
        ("import os", "os"),
        ("import socket", "socket"),
        ("from ..navigation.gnss_receiver import X", "not allowed"),
        ("from . import sibling", "relative imports"),
        ("x = eval('1')", "eval"),
        ("y = open('/etc/passwd')", "open"),
        ("z = ().__class__.__bases__", "__bases__"),
        ("w = getattr(object, 'x')", "getattr"),
    ],
)
def test_forbidden_constructs_are_rejected(snippet: str, reason: str) -> None:
    with pytest.raises(VettingError, match=reason):
        vet_module_source(GOOD + "\n" + snippet + "\n", MODULE)


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        ("class Echo(Module)", "class Other(Module)", "missing"),
        ("class Echo(Module)", "class Echo(object)", "subclass"),
        ('name = "echo"', 'name = "other"', "name must stay"),
        ('{"io.ping_out": Ping}', '{"io.other": Ping}', "publishes"),
        ('subscribes = {"io.ping_in": Ping}', "subscribes = SUBS", "dict literal"),
    ],
)
def test_interface_contract_must_not_change(old: str, new: str, reason: str) -> None:
    with pytest.raises(VettingError, match=reason):
        vet_module_source(GOOD.replace(old, new), MODULE)


def test_syntax_errors_are_rejected() -> None:
    with pytest.raises(VettingError, match="does not parse"):
        vet_module_source("def broken(:\n", MODULE)


def test_tests_may_import_pytest_and_the_package_only() -> None:
    good = "import pytest\nfrom demo.core.bus import MessageBus\n\ndef test_x():\n    pass\n"
    vet_test_source(good, "demo")
    with pytest.raises(VettingError, match="requests"):
        vet_test_source("import requests\n\ndef test_x():\n    pass\n", "demo")
    with pytest.raises(VettingError, match="no test functions"):
        vet_test_source("import pytest\n", "demo")
