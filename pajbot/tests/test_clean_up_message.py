def test_clean_up():
    from pajbot.utils import clean_up_message

    assert "󠀀" == "\U000e0000"

    assert "" == clean_up_message("")
    assert "" == clean_up_message("  ")
    assert "" == clean_up_message(" ")

    assert ". .timeout pajlada 5" == clean_up_message(".timeout pajlada 5")
    assert ". /timeout pajlada 5" == clean_up_message("/timeout pajlada 5")
    assert ". .timeout pajlada 5" == clean_up_message("   .timeout pajlada 5")
    assert ". /timeout pajlada 5" == clean_up_message(" /timeout pajlada 5")
    assert ".me xD" == clean_up_message(".me xD")
    assert "/me xD" == clean_up_message("/me xD")
    assert "/me xD" == clean_up_message("   /me xD")
    assert ".me xD" == clean_up_message("   .me xD")
    assert "asd" == clean_up_message("asd")
    assert "asd" == clean_up_message("    asd")
    for prefix in ["!", "$", "-", "<"]:
        assert f"\U000e0000{prefix}ping" == clean_up_message(f"{prefix}ping")
        assert f"/me \U000e0000{prefix}ping" == clean_up_message(f"/me {prefix}ping")
        assert f".me \U000e0000{prefix}ping" == clean_up_message(f".me {prefix}ping")
        assert f"\U000e0000{prefix}ping" == clean_up_message(f"    {prefix}ping")
        assert f".me \U000e0000{prefix}ping" == clean_up_message(f".me    {prefix}ping")
        assert f".me \U000e0000{prefix}ping" == clean_up_message(f" .me    {prefix}ping")
        assert f"/me \U000e0000{prefix}ping" == clean_up_message(f"/me    {prefix}ping")
        assert f"/me \U000e0000{prefix}ping" == clean_up_message(f" /me    {prefix}ping")

        assert f"\U000e0000{prefix}" == clean_up_message(f"{prefix}")
        assert f"/me \U000e0000{prefix}" == clean_up_message(f"/me {prefix}")
        assert f".me \U000e0000{prefix}" == clean_up_message(f".me {prefix}")
        assert f"\U000e0000{prefix}" == clean_up_message(f"    {prefix}")
        assert f".me \U000e0000{prefix}" == clean_up_message(f".me    {prefix}")
        assert f".me \U000e0000{prefix}" == clean_up_message(f" .me    {prefix}")
        assert f"/me \U000e0000{prefix}" == clean_up_message(f"/me    {prefix}")
        assert f"/me \U000e0000{prefix}" == clean_up_message(f" /me    {prefix}")
