import pytest
from pathlib      import Path
from _pytest.main import Session

# ---------------------------------------------------------
class Collector:
    """A minimal pytest plugin to collect test IDs."""
    # -----------------
    def __init__(self, path : Path):
        self._root_path = str(path)
        self.collected_test_ids : dict[int,str] = {}
    # -----------------
    def pytest_collection_finish(self, session: Session):
        """
        Called after all tests have been collected.
        """
        for index, item in enumerate(session.items):
            self.collected_test_ids[index] = self._root_path + '/' + item.nodeid
# ---------------------------------------------------------
def get_tests(path : Path) -> dict[int, str]:
    """
    Parameters
    ---------------
    test_path: Path where the search for tests will start

    Returns
    ---------------
    Dictionary mapping test index to command needed by pytest
    """
    collector = Collector(path=path)
    test_path = str(path)

    pytest.main([test_path, '--collect-only', '-q'], plugins=[collector])

    return collector.collected_test_ids
