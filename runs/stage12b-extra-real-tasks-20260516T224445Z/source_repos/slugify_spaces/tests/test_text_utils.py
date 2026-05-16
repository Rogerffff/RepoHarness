from text_utils import slugify


def test_slugify_basic():
    assert slugify('Hello World') == 'hello-world'

def test_slugify_extra_spaces():
    assert slugify('  Repo   Harness  ') == 'repo-harness'
