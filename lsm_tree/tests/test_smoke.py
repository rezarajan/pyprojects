import importlib

def test_import_package():
    pkg = importlib.import_module("lsm_tree")
    assert pkg is not None
