


def test_equality_delegation_nonexample():
    class Model(BaseModel):
        value: str

    model = Model(value='ordinary-matcher')

    class Matcher:
        def __init__(self, answer):
            self.answer = answer
            self.seen = None

        def __eq__(self, other):
            self.seen = other
            return self.answer

    for answer in (True, False, NotImplemented):
        matcher = Matcher(answer)
        assert (model == matcher) is (answer is True)
        assert matcher.seen is model

    assert model != {'value': 'ordinary-matcher'}
    assert model != object()
