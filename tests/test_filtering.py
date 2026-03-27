import unittest
import sys
import os

# Add the parent directory to sys.path to import generate_file_list
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_file_list import matches_filters

class TestFilteringLogic(unittest.TestCase):

    def test_no_filters(self):
        self.assertTrue(matches_filters("/some/path/file.txt", [], []))

    def test_dir_filter_and_logic(self):
        path = "/games/nintendo/mario.zip"
        self.assertTrue(matches_filters(path, ["games", "nintendo"], [], logic='AND'))
        self.assertFalse(matches_filters(path, ["games", "sony"], [], logic='AND'))

    def test_dir_filter_or_logic(self):
        path = "/games/nintendo/mario.zip"
        self.assertTrue(matches_filters(path, ["sony", "nintendo"], [], logic='OR'))
        self.assertFalse(matches_filters(path, ["sony", "sega"], [], logic='OR'))

    def test_file_filter_and_logic(self):
        path = "/games/nintendo/super_mario_bros.zip"
        self.assertTrue(matches_filters(path, [], ["super", "mario"], logic='AND'))
        self.assertFalse(matches_filters(path, [], ["super", "luigi"], logic='AND'))

    def test_file_filter_or_logic(self):
        path = "/games/nintendo/super_mario_bros.zip"
        self.assertTrue(matches_filters(path, [], ["luigi", "mario"], logic='OR'))
        self.assertFalse(matches_filters(path, [], ["luigi", "peach"], logic='OR'))

    def test_combine_logic_and(self):
        path = "/games/nintendo/mario.zip"
        # Dir matches, File matches -> True
        self.assertTrue(matches_filters(path, ["nintendo"], ["mario"], combine_logic='AND'))
        # Dir matches, File doesn't -> False
        self.assertFalse(matches_filters(path, ["nintendo"], ["luigi"], combine_logic='AND'))
        # Dir doesn't, File matches -> False
        self.assertFalse(matches_filters(path, ["sony"], ["mario"], combine_logic='AND'))

    def test_combine_logic_or(self):
        path = "/games/nintendo/mario.zip"
        # Dir matches, File matches -> True
        self.assertTrue(matches_filters(path, ["nintendo"], ["mario"], combine_logic='OR'))
        # Dir matches, File doesn't -> True
        self.assertTrue(matches_filters(path, ["nintendo"], ["luigi"], combine_logic='OR'))
        # Dir doesn't, File matches -> True
        self.assertTrue(matches_filters(path, ["sony"], ["mario"], combine_logic='OR'))
        # Neither matches -> False
        self.assertFalse(matches_filters(path, ["sony"], ["luigi"], combine_logic='OR'))

    def test_case_insensitivity(self):
        path = "/Games/Nintendo/Mario.zip"
        self.assertTrue(matches_filters(path, ["games"], ["mario"]))

    def test_path_normalization(self):
        path = "Games\\Nintendo\\Mario.zip"
        self.assertTrue(matches_filters(path, ["games/nintendo"], ["mario"]))

if __name__ == '__main__':
    unittest.main()
