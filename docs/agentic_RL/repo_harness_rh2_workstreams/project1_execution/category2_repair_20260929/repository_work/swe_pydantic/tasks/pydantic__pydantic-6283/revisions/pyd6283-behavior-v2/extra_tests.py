


def test_root_model_construct_equality_nonexample():
    class TextRoot(RootModel):
        root: str

    assert TextRoot('another') == TextRoot.model_construct('another')


def test_root_model_construct_preserves_private_default():
    class PrivateRoot(RootModel[int]):
        _secret: str = PrivateAttr(default='abc')

    assert PrivateRoot.model_construct(42)._secret == 'abc'
