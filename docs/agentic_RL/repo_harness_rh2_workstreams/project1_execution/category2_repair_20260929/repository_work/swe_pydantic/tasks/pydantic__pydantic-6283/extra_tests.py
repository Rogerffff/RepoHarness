


def test_root_model_construct_equality_nonexample():
    class TextRoot(RootModel):
        root: str

    assert TextRoot('another') == TextRoot.model_construct('another')
