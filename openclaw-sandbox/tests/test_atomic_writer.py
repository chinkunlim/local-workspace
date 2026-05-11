import json
import os

from core.utils.atomic_writer import AtomicWriter


def test_atomic_write_text(tmp_workspace):
    file_path = os.path.join(tmp_workspace, "test.txt")

    # Test initial write
    AtomicWriter.write_text(file_path, "Hello World")
    with open(file_path, encoding="utf-8") as f:
        assert f.read() == "Hello World"

    # Test overwrite
    AtomicWriter.write_text(file_path, "Updated Content")
    with open(file_path, encoding="utf-8") as f:
        assert f.read() == "Updated Content"


def test_atomic_write_json(tmp_workspace):
    file_path = os.path.join(tmp_workspace, "test.json")
    data = {"key": "value"}

    AtomicWriter.write_json(file_path, data)
    with open(file_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data


def test_atomic_write_creates_directories(tmp_workspace):
    file_path = os.path.join(tmp_workspace, "deep", "nested", "test.txt")
    AtomicWriter.write_text(file_path, "Nested")

    assert os.path.exists(file_path)
    with open(file_path, encoding="utf-8") as f:
        assert f.read() == "Nested"
