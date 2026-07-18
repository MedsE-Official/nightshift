import json

from artifacts import ArtifactStore, CycleIdentity, Historian


def test_artifact_store_links_feature_task_cycle_and_version(tmp_path):
    store = ArtifactStore(tmp_path, CycleIdentity("FEAT-1", "TASK-2", "cycle-3", "0.3.0", "abc"))
    identity = json.loads((store.root / "identity.json").read_text())
    assert identity["feature_id"] == "FEAT-1"
    assert identity["task_id"] == "TASK-2"
    assert identity["nightshift_version"] == "0.3.0"


def test_historian_writes_retrospective(tmp_path):
    store = ArtifactStore(tmp_path, CycleIdentity("F", "T", "C", "v", "abc"))
    path = Historian().record_retrospective(
        store=store, approved=True, attempts=1,
        review={"summary": "good"}, verification={"test": {"passed": True}},
        contract_violations=[],
    )
    data = json.loads(path.read_text())
    assert data["went_well"]
    assert data["continue"] == ["Use structured architecture contracts."]
