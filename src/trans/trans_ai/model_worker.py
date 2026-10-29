from .rate_limiter import AsyncRateLimiter


class ModelWorker:
    def __init__(self, model_name, rpm, max_concurrent, temperature, br_start=0, isno_x=False, thinking_budget=None):
        self.model_name = str(model_name).strip()
        self.rpm = max(1, int(rpm))
        self.max_concurrent = max(1, int(max_concurrent))
        self.temperature = float(temperature)
        self.br_start = max(0, int(br_start))
        self.isno_x = bool(isno_x)
        self.thinking_budget = thinking_budget
        self.rate_limiter = AsyncRateLimiter(self.rpm)

    def __repr__(self):
        return f"ModelWorker(model={self.model_name},rpm={self.rpm},concurrent={self.max_concurrent},temperature={self.temperature},br_start={self.br_start},isno_x={self.isno_x},thinking={self.thinking_budget})"


def _parse_models(model_name):
    if isinstance(model_name, str):
        models = [x.strip() for x in model_name.split(',') if x.strip()]
    else:
        models = [str(x).strip() for x in model_name if str(x).strip()]

    if not models:
        raise ValueError('사용할 모델이 없습니다.')

    return models


def _normalize_model_values(value, count, name):
    if isinstance(value, (tuple, list)):
        values = list(value)
        if len(values) == 1 and count > 1:
            values = values * count
    elif isinstance(value, str) and ',' in value:
        values = [x.strip() for x in value.split(',') if x.strip()]
    else:
        values = [value]

    if len(values) == 1 and count > 1:
        values = values * count

    if len(values) != count:
        raise ValueError(f'{name} 개수 불일치: 모델 {count}개 / {name} {len(values)}개')

    return values


def _create_model_workers(model_name, rpm, max_concurrent, temperature, br_start=0, isno_x=False, thinking_budget=None):
    models = _parse_models(model_name)
    rpms = _normalize_model_values(rpm, len(models), 'RPM')
    concurrencies = _normalize_model_values(max_concurrent, len(models), '동시 작업수')
    temperatures = _normalize_model_values(temperature, len(models), 'Temperature')
    br_starts = _normalize_model_values(br_start, len(models), '분할 시작')
    isno_xs = _normalize_model_values(isno_x, len(models), '검열 건너뛰기')
    thinking_budgets = _normalize_model_values(thinking_budget, len(models), '추론')
    workers = []
    for i, model in enumerate(models):
        workers.append(ModelWorker(
            model, rpms[i], concurrencies[i], temperatures[i], br_starts[i], isno_xs[i], thinking_budgets[i]
        ))
    return workers