import tempfile
from pathlib import Path

import setup_models as sm


def test_parse_chunk():
    assert sm.parse_chunk('{"status":"pulling","completed":10,"total":100}') == ("pulling", 10, 100)
    assert sm.parse_chunk('{"status":"verifying"}') == ("verifying", None, None)


def test_config_roundtrip(tmpdir):
    sm.CONFIG_PATH = Path(tmpdir) / "config.json"
    assert sm.load_config() == sm.DEFAULTS  # defaults when file absent
    cfg = sm.load_config()
    cfg["pulled_models"].append("x:7b")
    cfg["active_model"] = "x:7b"
    sm.save_config(cfg)
    assert sm.load_config() == {"active_model": "x:7b", "pulled_models": ["x:7b"]}


if __name__ == "__main__":
    test_parse_chunk()
    with tempfile.TemporaryDirectory() as d:
        test_config_roundtrip(d)
    print("ok")
