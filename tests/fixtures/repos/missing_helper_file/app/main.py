from app.helpers import normalize_name


def greeting(name: str) -> str:
    return f"Hello, {normalize_name(name)}!"
