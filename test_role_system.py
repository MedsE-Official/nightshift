from role_system import ModelManager, ModelRegistry, Role, RoleProfile, RoleRunner


def test_registry_loads_role_specific_models():
    registry = ModelRegistry.from_config({
        "model": "general",
        "aider_model": "coder",
        "roles": {
            "architect": {"model": "reasoner", "temperature": 0.2},
            "reviewer": {"model": "reviewer"},
        },
    })
    assert registry.profile_for(Role.ARCHITECT).model == "reasoner"
    assert registry.profile_for(Role.BUILDER).model == "coder"
    assert registry.profile_for(Role.PLANNER).model == "general"


def test_manager_keeps_only_one_profile_loaded():
    events = []
    manager = ModelManager(
        loader=lambda profile: events.append(("load", profile.model)),
        unloader=lambda profile: events.append(("unload", profile.model)),
    )
    first = RoleProfile(Role.ARCHITECT, "a")
    second = RoleProfile(Role.BUILDER, "b")
    manager.ensure_loaded(first)
    manager.ensure_loaded(first)
    manager.ensure_loaded(second)
    assert events == [("load", "a"), ("unload", "a"), ("load", "b")]


def test_role_runner_passes_profile_to_operation():
    registry = ModelRegistry.from_config({"model": "general", "aider_model": "coder"})
    runner = RoleRunner(registry, ModelManager())
    assert runner.run(Role.ARCHITECT, lambda profile: profile.model) == "general"
