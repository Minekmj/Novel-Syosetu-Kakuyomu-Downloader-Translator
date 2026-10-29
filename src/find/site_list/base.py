from enum import IntEnum

class Sites(IntEnum):
    NAROU = 1
    KAKUYOMU = 2
    HAMELLEUN = 3
    MIDNIGHT = 4
    NOCTURNE = 5
    HAMELLEUN18 = 6

SITES = {}
SITE_REGISTRY = {}

class BaseSite:
    site = None
    name = ''
    search_class = None
    has_star = False

    def point_text(self, value):
        return f'{value}'

    def setup_ui(self, window, layout):
        pass

    def build_params(self, window):
        return {}

def register_site(cls=None, **kwargs):
    def decorator(target_cls):
        for k, v in kwargs.items():
            setattr(target_cls, k, v)
        instance = target_cls()
        if instance.site is None:
            raise ValueError(f'{target_cls.__name__}의 site 속성이 정의되지 않았습니다.')
        SITE_REGISTRY[instance.site] = instance
        SITES[instance.site] = {
            'name': instance.name,
            'search_class': instance.search_class,
            'point_text': instance.point_text,
            'has_star': instance.has_star,
            'ui_setup': instance.setup_ui,
            'build_params': instance.build_params,
        }
        return target_cls

    if cls is not None:
        return decorator(cls)
    return decorator

def get_site(site):
    if site not in SITES:
        raise ValueError(f'지원하지 않는 사이트입니다: {site}')
    return SITES[site]

def get_site_name(site):
    return get_site(site)['name']

def get_search_class(site):
    return get_site(site)['search_class']

def site_point_text(site, value):
    return get_site(site)['point_text'](value)

def site_is_kaku(site):
    return site == Sites.KAKUYOMU

def site_build_params(window):
    return get_site(window.site)['build_params'](window)