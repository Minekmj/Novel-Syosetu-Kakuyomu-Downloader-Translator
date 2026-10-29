def create_model_config(model, base=None):
    base = base or {}
    return {
        'model': str(model).strip(),
        'rpm': int(base.get('rpm', 15)),
        'temperature': float(base.get('temperature', 0.1)),
        'concurrency': int(base.get('concurrency', 4)),
        'br_start': int(base.get('br_start', 0)),
        'isno_x': bool(base.get('isno_x', False)),
        'thinking_budget': str(base.get('thinking_budget', '기본값'))
    }


def models_from_data(models, defaults=None):
    defaults = defaults or {}
    result, used = [], set()

    for item in models if isinstance(models, list) else []:
        raw = {'model': item} if isinstance(item, str) else item if isinstance(item, dict) else {}
        model = str(raw.get('model', '')).strip()
        key = model.casefold()

        if model and key not in used:
            used.add(key)
            result.append(create_model_config(model, {**defaults, **raw}))

    return result