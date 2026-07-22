import pytest

from prompt_catalog import PromptCatalog


def test_prompt_catalog_returns_role_prompt():
    catalog = PromptCatalog.from_dict({"prompts": {"builder": "Build carefully."}})
    assert catalog.get("builder") == "Build carefully."


def test_prompt_catalog_reports_missing_role():
    catalog = PromptCatalog.from_dict({"prompts": {"builder": "Build."}})
    with pytest.raises(KeyError, match="reviewer"):
        catalog.get("reviewer")
