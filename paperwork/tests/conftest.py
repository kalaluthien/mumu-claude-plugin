"""A pytest session over every test file of this folder takes a slot at the machine gate before its first test; a
session over fewer files takes none, so a single-file run never waits behind full suites."""
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("machine_gate", HERE.parent / "lib" / "machine_gate.py")
machine_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(machine_gate)


def pytest_collection_finish(session):
    collected = {pathlib.Path(str(item.fspath)).resolve() for item in session.items}
    if collected >= set(HERE.glob("test_*.py")):
        machine_gate.queue("paperwork tests")
