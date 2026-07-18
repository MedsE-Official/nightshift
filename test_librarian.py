from librarian import build_repo_map


def test_repo_map_is_deterministic_and_marks_candidate_files(tmp_path):
    (tmp_path / "b.py").write_text("")
    (tmp_path / "a.py").write_text("")
    result = build_repo_map(tmp_path, candidate_files=["b.py"])
    assert result.splitlines() == ["- a.py", "* b.py"]
