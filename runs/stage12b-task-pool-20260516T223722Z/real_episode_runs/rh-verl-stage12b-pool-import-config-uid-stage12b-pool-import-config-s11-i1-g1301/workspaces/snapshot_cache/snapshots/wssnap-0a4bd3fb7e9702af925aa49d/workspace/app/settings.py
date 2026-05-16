DEFAULT_FLAGS = {"search": True}


def get_feature_flag(name: str) -> bool:
    return DEFAULT_FLAGS[name]
