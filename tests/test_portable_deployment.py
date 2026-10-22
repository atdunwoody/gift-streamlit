"""Ensure a moved repository does not recompute the bundled GIFT hydraulics."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import prepare_data


def test_bundled_data_is_current(monkeypatch):
    # Preparing hundreds of hydraulic curves should not happen at startup.
    def disallow_model(*args, **kwargs):
        raise AssertionError("Existing hydraulics should be loaded, not rebuilt")

    monkeypatch.setattr(prepare_data, "prepare_network", disallow_model)
    result = prepare_data.ensure_prepared_data()
    assert result["rebuilt"] is False
    assert result["manifest"]["schemaVersion"] == prepare_data.SCHEMA_VERSION
    assert result["manifest"]["configuration"]["network_path"].startswith("inputs/")
    assert result["manifest"]["configuration"]["output_directory"] == "data"


def test_manifest_fingerprint_survives_relocation(tmp_path, monkeypatch):
    # The manifest is precomputed on Windows but must validate after a move
    # to an arbitrary directory, such as Streamlit Community Cloud.
    expected = prepare_data.source_state(prepare_data.load_settings(),
                                        prepare_data.build_options(prepare_data.load_settings()))[0]
    relocated = tmp_path / "hosted-checkout"
    relocated.mkdir()
    for folder in ("inputs", "data", "model", "tools"):
        shutil.copytree(ROOT / folder, relocated / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for filename in ("settings.py", "prepare_data.py"):
        shutil.copy2(ROOT / filename, relocated / filename)
    monkeypatch.setattr(prepare_data, "ROOT", relocated)
    settings = prepare_data.load_settings()
    options = prepare_data.build_options(settings)
    actual = prepare_data.source_state(settings, options)[0]
    assert actual == expected
    assert prepare_data.current_manifest(options["output_directory"], actual) is not None
