from app import get_feature_flag


def test_known_flag():
    assert get_feature_flag("search") is True


def test_unknown_flag_defaults_to_false():
    assert get_feature_flag("unknown") is False
