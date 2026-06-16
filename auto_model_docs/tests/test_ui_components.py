from studio.ui_components import format_project_context_label


def test_format_project_context_label_splits_on_slash():
    assert format_project_context_label("integration-test/modeldocs-target-bgp") == (
        "integration-test / modeldocs-target-bgp"
    )


def test_format_project_context_label_owner_project():
    assert format_project_context_label("alice/my-project") == "alice / my-project"


def test_format_project_context_label_no_slash_unchanged():
    assert format_project_context_label("abc-123-def") == "abc-123-def"


def test_format_project_context_label_empty():
    assert format_project_context_label("") == ""
    assert format_project_context_label(None) == ""
