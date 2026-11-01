from src.ai import AiRoute

TARGET_NAMES = AiRoute.TARGET_NAMES
detect_ai_target = AiRoute.detect_target


def create_model_config(model, base=None):
    base = base or {}
    model_name = str(model).strip()
    target_int = int(base.get('ai_target', base.get('target', AiRoute.detect_target(model_name))))

    defaults = AiRoute.get_default_config(target_int)

    return {
        'ai_target': target_int,
        'model': model_name,
        'rpm': int(base.get('rpm', defaults['rpm'])),
        'temperature': float(base.get('temperature', defaults['temperature'])),
        'concurrency': int(base.get('concurrency', defaults['concurrency'])),
        'br_start': int(base.get('br_start', defaults['br_start'])),
        'isno_x': bool(base.get('isno_x', defaults['isno_x'])),
        'thinking_budget': str(base.get('thinking_budget', defaults['thinking_budget']))
    }


def models_from_data(models, defaults=None):
    defaults = defaults or {}
    result, used = [], set()

    for item in models if isinstance(models, list) else []:
        raw = {'model': item} if isinstance(item, str) else item if isinstance(item, dict) else {}
        model = str(raw.get('model', '')).strip()
        if not model:
            continue

        target_int = int(raw.get('ai_target', AiRoute.detect_target(model)))
        key = (target_int, model.casefold())

        if key not in used:
            used.add(key)
            result.append(create_model_config(model, {**defaults, **raw, 'ai_target': target_int}))

    return result