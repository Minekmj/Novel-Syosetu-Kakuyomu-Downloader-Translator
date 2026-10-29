class BaseSearchSite:
    site_id = ""
    display_name = ""

    @classmethod
    def fetch_search_results(cls, params: dict) -> dict:
        raise NotImplementedError

    @classmethod
    def fetch_detail_description(cls, work_url: str) -> str:
        raise NotImplementedError


class SearchRegistry:
    _registry = {}

    @classmethod
    def register(cls, site_class):
        site_id = getattr(site_class, "site_id", site_class.__name__)
        cls._registry[site_id] = site_class
        return site_class

    @classmethod
    def get(cls, site_id):
        return cls._registry.get(site_id)

    @classmethod
    def get_all(cls):
        return list(cls._registry.values())

    @classmethod
    def get_dict(cls):
        return dict(cls._registry)


def register_search(cls):
    return SearchRegistry.register(cls)