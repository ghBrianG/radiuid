#!/usr/bin/env python3
"""
Tests for UserInterface class
"""

from radiuid.ui.interface import UserInterface


class TestUserInterface:
    """Test cases for UserInterface class"""

    def test_color_output(self, user_interface):
        """Test color formatting"""
        colored = user_interface.color("test", user_interface.green)
        assert "test" in colored
        assert "\033[" in colored  # ANSI escape code

    def test_color_with_all_colors(self, user_interface):
        """Test all color options"""
        colors = [
            user_interface.red,
            user_interface.green,
            user_interface.yellow,
            user_interface.blue,
            user_interface.magenta,
            user_interface.cyan,
        ]
        for color in colors:
            result = user_interface.color("test", color)
            assert "test" in result

    def test_make_table(self, user_interface):
        """Test table generation"""
        columns = ["Name", "Value"]
        data = [
            {"Name": "item1", "Value": "100"},
            {"Name": "item2", "Value": "200"},
        ]
        table = user_interface.make_table(columns, data)
        assert "Name" in table
        assert "Value" in table
        assert "item1" in table
        assert "100" in table

    def test_make_table_empty(self, user_interface):
        """Test table generation with empty data"""
        columns = ["Name", "Value"]
        data = []
        table = user_interface.make_table(columns, data)
        assert "Name" in table
        assert "Value" in table

    def test_yesorno_valid_inputs(self, user_interface, monkeypatch):
        """Test yes/no input handling"""
        # Test 'yes' input
        monkeypatch.setattr('builtins.input', lambda _: 'yes')
        result = user_interface.yesorno("Test question?")
        assert result == 'yes'

        # Test 'no' input
        monkeypatch.setattr('builtins.input', lambda _: 'no')
        result = user_interface.yesorno("Test question?")
        assert result == 'no'

        # Test 'y' input
        monkeypatch.setattr('builtins.input', lambda _: 'y')
        result = user_interface.yesorno("Test question?")
        assert result == 'yes'

        # Test 'n' input
        monkeypatch.setattr('builtins.input', lambda _: 'n')
        result = user_interface.yesorno("Test question?")
        assert result == 'no'


class TestUserInterfaceLegacyAlias:
    """Test legacy alias compatibility"""

    def test_legacy_import(self):
        """Test that legacy class name still works"""
        from radiuid import user_interface
        ui = user_interface()
        assert isinstance(ui, UserInterface)
