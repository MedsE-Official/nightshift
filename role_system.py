from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class Role(str, Enum):
    PLANNER = "planner"
    ARCHITECT = "architect"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    HISTORIAN = "historian"
    LIBRARIAN = "librarian"


@dataclass(frozen=True)
class RoleProfile:
    role: Role
    model: str
    provider: str = "ollama"
    system_prompt: str | None = None
    tools: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    context_policy: str = "isolated"
    output_schema: str | None = None
    temperature: float = 0.1

    @classmethod
    def from_dict(cls, role_name: str, data: Mapping[str, Any]) -> "RoleProfile":
        if not isinstance(data, Mapping):
            raise ValueError(f"Role profile '{role_name}' must be an object")
        try:
            role = Role(role_name)
        except ValueError as exc:
            raise ValueError(f"Unknown role: {role_name}") from exc
        model = data.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"Role profile '{role_name}' requires a model")
        return cls(
            role=role,
            model=model.strip(),
            provider=str(data.get("provider", "ollama")),
            system_prompt=data.get("system_prompt"),
            tools=tuple(str(item) for item in data.get("tools", [])),
            permissions=tuple(str(item) for item in data.get("permissions", [])),
            context_policy=str(data.get("context_policy", "isolated")),
            output_schema=data.get("output_schema"),
            temperature=float(data.get("temperature", 0.1)),
        )


class ModelRegistry:
    def __init__(self, profiles: Mapping[Role, RoleProfile]):
        self._profiles = dict(profiles)

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "ModelRegistry":
        roles_data = config.get("roles", {})
        if not isinstance(roles_data, Mapping):
            raise ValueError("config.roles must be an object")

        profiles: dict[Role, RoleProfile] = {}
        for role in Role:
            raw = roles_data.get(role.value)
            if raw is None:
                fallback_model = (
                    config.get("aider_model")
                    if role is Role.BUILDER
                    else config.get("model")
                )
                if not isinstance(fallback_model, str) or not fallback_model:
                    continue
                raw = {"model": fallback_model}
            profiles[role] = RoleProfile.from_dict(role.value, raw)
        return cls(profiles)

    def profile_for(self, role: Role) -> RoleProfile:
        try:
            return self._profiles[role]
        except KeyError as exc:
            raise KeyError(f"No role profile configured for {role.value}") from exc


class ModelManager:
    """Tracks one active model and delegates lifecycle operations.

    Lifecycle callbacks are optional so orchestration stays independent of a
    specific inference provider. A provider adapter can later implement actual
    Ollama load/unload calls without changing role orchestration.
    """

    def __init__(
        self,
        *,
        loader: Callable[[RoleProfile], None] | None = None,
        unloader: Callable[[RoleProfile], None] | None = None,
    ) -> None:
        self._loader = loader
        self._unloader = unloader
        self._loaded: RoleProfile | None = None

    @property
    def loaded_profile(self) -> RoleProfile | None:
        return self._loaded

    def ensure_loaded(self, profile: RoleProfile) -> None:
        if self._loaded == profile:
            return
        if self._loaded is not None:
            self.unload()
        if self._loader is not None:
            self._loader(profile)
        self._loaded = profile

    def unload(self) -> None:
        if self._loaded is None:
            return
        previous = self._loaded
        self._loaded = None
        if self._unloader is not None:
            self._unloader(previous)


class RoleRunner:
    def __init__(self, registry: ModelRegistry, manager: ModelManager) -> None:
        self._registry = registry
        self._manager = manager

    def run(self, role: Role, operation: Callable[[RoleProfile], Any]) -> Any:
        profile = self._registry.profile_for(role)
        self._manager.ensure_loaded(profile)
        return operation(profile)
