"""Run project checks with python test_all.py."""

import stego_text


def test_text():
    memo = stego_text.MEMO
    assert stego_text.coverage(memo) == 8
    for recipient_id in range(1, 256):
        personalised = stego_text.embed_id(memo, recipient_id)
        assert stego_text.extract_id(personalised)[0] == recipient_id
    repeated = stego_text.embed_id(f"{memo}\n{memo}", 5)
    assert stego_text.extract_id(repeated.splitlines()[1])[0] == 5
    assert stego_text.extract_id("The large launch")[0] is None
    assert stego_text.extract_id(memo + " large")[0] is None


if __name__ == "__main__":
    test_text()
    print("All tests passed")
