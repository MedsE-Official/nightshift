from knowledge_base import KnowledgeBase


def test_knowledge_base_filters_entries_by_role():
    knowledge = KnowledgeBase.from_dict({
        "entries": [
            {"id": "a", "title": "Builder", "content": "Build.", "tags": ["builder"]},
            {"id": "b", "title": "Review", "content": "Review.", "tags": ["reviewer"]},
            {"id": "c", "title": "Shared", "content": "Shared.", "tags": []},
        ]
    })

    rendered = knowledge.render(role="builder")

    assert "Build." in rendered
    assert "Shared." in rendered
    assert "Review." not in rendered
