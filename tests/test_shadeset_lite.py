import shadeset_lite


def test_one(data_path):
    assert shadeset_lite.get_selected() == []
