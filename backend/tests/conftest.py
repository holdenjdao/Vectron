from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vectron.api.app import create_app
from vectron.blueprints.catalog import BlueprintCatalog
from vectron.config import Settings
from vectron.service import Factory


@pytest.fixture(scope="session")
def catalog() -> BlueprintCatalog:
    return BlueprintCatalog.load()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", llm_provider="offline", max_concurrency=4)


@pytest.fixture
def factory(settings: Settings, catalog: BlueprintCatalog) -> Factory:
    return Factory(settings, catalog=catalog)


@pytest.fixture
def client(factory: Factory) -> Iterator[TestClient]:
    with TestClient(create_app(factory)) as test_client:
        yield test_client
