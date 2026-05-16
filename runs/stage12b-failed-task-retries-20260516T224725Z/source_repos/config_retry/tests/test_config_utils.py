from config_utils import get_timeout


def test_known_service():
    assert get_timeout('search') == 5

def test_unknown_service_default():
    assert get_timeout('missing') == 30
