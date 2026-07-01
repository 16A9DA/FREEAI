import json

from freecode.agent import _new_project_folder


def test_detects_scaffolded_folder():
    assert _new_project_folder("create_file", {"path": "myapp/index.html"}) == "myapp"
    assert _new_project_folder("write_file", {"path": "site/css/x.css"}) == "site"
    assert _new_project_folder("run_command", {"command": "mkdir -p build"}) == "build"


def test_ignores_root_files_and_reads():
    assert _new_project_folder("create_file", {"path": "README.md"}) is None
    assert _new_project_folder("create_file", {"path": "/abs/x.py"}) is None
    assert _new_project_folder("run_command", {"command": "ls"}) is None
    assert _new_project_folder("read_file", {"path": "a/b"}) is None


def test_duplicate_call_signature_matches():
    sig = lambda n, a: (n, json.dumps(a, sort_keys=True, default=str))
    assert sig("read_file", {"path": "x"}) == sig("read_file", {"path": "x"})
    assert sig("read_file", {"path": "x"}) != sig("read_file", {"path": "y"})


if __name__ == "__main__":
    test_detects_scaffolded_folder()
    test_ignores_root_files_and_reads()
    test_duplicate_call_signature_matches()
    print("ok")
