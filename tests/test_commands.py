# mock user B)
class User:
    def __init__(self, moderator, level):
        self.moderator = moderator
        self.level = level


def test_command_permission_mod_only():
    from pajbot.models.command import Command

    tests = [
        [
            "User with level 100 can execute command with level 100",
            Command(mod_only=False, level=100),  # Command to test agains
            User(False, 100),  # User to test with
            True,  # Whether the user should be able to use the command or not
        ],
        [
            "User with level 100 CANNOT execute command with level 101",
            Command(mod_only=False, level=101),
            User(False, 100),
            False,
        ],
        [
            "User with level 101 can execute command with level 101",
            Command(mod_only=False, level=101),
            User(False, 101),
            True,
        ],
        [
            "User with level 100 CANNOT execute command with level 500",
            Command(mod_only=False, level=500),
            User(False, 100),
            False,
        ],
        [
            "User with level 500 can execute command with level 500",
            Command(mod_only=False, level=500),
            User(False, 500),
            True,
        ],
        [
            "Moderator with level 100 can execute mod_only command with level 100",
            Command(mod_only=True, level=100),
            User(True, 100),
            True,
        ],
        [
            "User with level 100 CANNOT execute mod_only command with level 100",
            Command(mod_only=True, level=100),
            User(False, 100),
            False,
        ],
        [
            "Moderator with level 500 can execute mod_only command with level 500",
            Command(mod_only=True, level=500),
            User(True, 500),
            True,
        ],
        [
            "Moderator with level 100 CANNOT execute mod_only command with level 500",
            Command(mod_only=True, level=500),
            User(True, 100),
            False,
        ],
        [
            "User with level 500 can execute mod_only command with level 499",
            Command(mod_only=True, level=499),
            User(False, 500),
            True,
        ],
        [
            "User with level 500 can execute mod_only command with level 500",
            Command(mod_only=True, level=500),
            User(False, 500),
            True,
        ],
        [
            "User with level 500 CANNOT execute mod_only command with level 501",
            Command(mod_only=True, level=501),
            User(False, 500),
            False,
        ],
    ]

    for t in tests:
        name = t[0]
        command = t[1]
        source = t[2]
        expected_result = t[3]

        actual_result = command.can_run_command(source, False)

        print(f"Making sure {name} works")
        assert actual_result == expected_result
