TIMEOUTS = {"search": 5, "index": 10}


def get_timeout(service: str) -> int:
    return TIMEOUTS[service]
