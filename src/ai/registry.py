from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class AiProviderInfo:
    target: int
    name: str
    model_class: Type
    default_model: str
    popular_models: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    matcher: Optional[Callable[[str], bool]] = None
    default_config: Dict[str, Any] = field(default_factory=dict)
    is_default_target: bool = False


class AiRegistry:
    _providers: Dict[int, AiProviderInfo] = {}

    @classmethod
    def register(
        cls,
        target: int,
        name: str,
        default_model: str,
        popular_models: Optional[List[str]] = None,
        patterns: Optional[List[str]] = None,
        matcher: Optional[Callable[[str], bool]] = None,
        default_config: Optional[Dict[str, Any]] = None,
        is_default: bool = False,
    ):
        def decorator(model_class: Type):
            cfg = {
                "rpm": 15,
                "temperature": 0.1,
                "concurrency": 4,
                "br_start": 0,
                "isno_x": False,
                "thinking_budget": "기본값"
            }
            if default_config:
                cfg.update(default_config)

            info = AiProviderInfo(
                target=int(target),
                name=name,
                model_class=model_class,
                default_model=default_model,
                popular_models=popular_models or [default_model],
                patterns=patterns or [],
                matcher=matcher,
                default_config=cfg,
                is_default_target=is_default,
            )
            cls._providers[int(target)] = info
            return model_class

        return decorator

    @classmethod
    def get(cls, target: int) -> Optional[AiProviderInfo]:
        return cls._providers.get(int(target))

    @classmethod
    def get_all(cls) -> Dict[int, AiProviderInfo]:
        return cls._providers

    @classmethod
    def get_default_target(cls) -> int:
        for target, info in cls._providers.items():
            if info.is_default_target:
                return target
        if cls._providers:
            return next(iter(cls._providers.keys()))
        return 0

    @classmethod
    def detect_target(cls, model_name: str) -> int:
        m = str(model_name).strip().lower()
        if not m:
            return cls.get_default_target()

        for target, info in cls._providers.items():
            if info.matcher and info.matcher(m):
                return target

        matches = []
        for target, info in cls._providers.items():
            for p in info.patterns:
                p_lower = p.lower()
                if m.startswith(p_lower) or p_lower in m:
                    matches.append((len(p_lower), target))

        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            return matches[0][1]

        return cls.get_default_target()


register_ai = AiRegistry.register