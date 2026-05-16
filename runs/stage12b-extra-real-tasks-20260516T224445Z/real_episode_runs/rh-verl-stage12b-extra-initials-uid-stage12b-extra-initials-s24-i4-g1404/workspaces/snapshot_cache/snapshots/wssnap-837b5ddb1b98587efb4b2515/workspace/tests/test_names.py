from names import initials


def test_two_words():
    assert initials('repo harness') == 'RH'

def test_extra_spaces():
    assert initials('  ada   lovelace ') == 'AL'
