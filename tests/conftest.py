import os

import pytest


def pytest_sessionstart():
    from maya import standalone
    standalone.initialize()


def pytest_sessionfinish():
    from maya import standalone
    standalone.uninitialize()


@pytest.fixture
def test_data():

    class TestData:
        path = os.path.join(
            os.path.dirname(__file__),
            'data',
        ).replace('\\', '/')

        def join(self, *parts):
            return os.path.join(self.path, *parts).replace('\\', '/')

    return TestData()
