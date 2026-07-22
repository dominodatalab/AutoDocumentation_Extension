import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "extension_manifest.json"


def test_extension_manifest_exists():
    assert MANIFEST_PATH.is_file()


def test_extension_manifest_required_fields():
    manifest = json.loads(MANIFEST_PATH.read_text())

    assert manifest["manifestSchemaVersion"] == 1
    assert manifest["project"]["visibility"] == "Private"
    assert manifest["app"]["entryPoint"] == "app.sh"
    assert manifest["app"]["mountDatasets"] is True
    assert manifest["app"]["vanityUrl"] == "modeldocs"
    assert (
        manifest["app"]["computeEnvironment"]["customEnvironment"]["buildArgs"][
            "EXTENSION_VERSION"
        ]
        == "v1.0.0"
    )
    assert manifest["extension"]["uiMountPointTypeConfigs"]["projectSidebar"]["enabled"]
    assert manifest["extension"]["uiMountPointTypeConfigs"]["model"]["enabled"]
