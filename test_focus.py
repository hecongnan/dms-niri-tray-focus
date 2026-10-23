import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('focus', Path(__file__).with_name('focus-tray-window.py'))
focus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(focus)


def entry(number, label, **properties):
    return {'data': [number, {'label': {'data': label}, **properties}, []]}


class FocusTests(unittest.TestCase):
    def test_recent_window_and_pid_matching(self):
        windows = [{'id': 1, 'app_id': 'com.follow.clash', 'pid': 7, 'focus_timestamp': {'secs': 1}},
                   {'id': 2, 'app_id': 'com.follow.clash', 'pid': 7, 'focus_timestamp': {'secs': 2}}]
        self.assertEqual(focus.choose_window(windows, {'flclash'}, {7})['id'], 2)
        self.assertIsNone(focus.choose_window(windows, {'clash'}, set()))

    def test_show_entry_ignores_toggles_hidden_disabled_and_quit(self):
        layout = [0, {}, [entry(1, '暂停'), entry(2, 'Show', **{'toggle-type': {'data': 'checkmark'}}),
                          entry(3, '显示', enabled={'data': False}),
                          entry(4, 'Show', visible={'data': False}), entry(5, '退出'), entry(103, '_Show')]]
        self.assertEqual(focus.show_menu_entry(layout), 103)
        self.assertIsNone(focus.show_menu_entry([0, {}, [entry(5, '退出')]]))
        self.assertEqual(focus.show_menu_entry([0, {}, [entry(8, '顯示')]]), 8)

    def test_dynamic_show_id_is_used(self):
        layout = [0, {}, [entry(19, '全局'), entry(103, '显示'), entry(27, '退出')]]
        with patch.object(focus, 'run', side_effect=[json.dumps({'data': '/menu'}),
                    json.dumps({'data': [3, layout]}), '']) as run:
            self.assertTrue(focus.show_flclash(':1.20', '/tray'))
        self.assertEqual(run.call_args.args[-6:], ('isvu', '103', 'clicked', 'i', '0', '0'))

    def test_hidden_flclash_is_restored_then_focused(self):
        window = {'id': 23, 'pid': 7, 'app_id': 'com.follow.clash'}
        with patch.object(sys, 'argv', ['helper', 'FlClash']), \
             patch.object(focus, 'matching_trays', return_value=[(':1.20', '/tray', 7)]), \
             patch.object(focus, 'show_flclash', return_value=True) as show, \
             patch.object(focus, 'run', side_effect=['[]', json.dumps([window]), '']) as run:
            self.assertEqual(focus.main(), 0)
            show.assert_called_once_with(':1.20', '/tray')
            self.assertEqual(run.call_args.args, ('niri', 'msg', 'action', 'focus-window', '--id', '23'))

    def test_visible_flclash_does_not_call_show(self):
        window = {'id': 23, 'pid': 7, 'app_id': 'com.follow.clash'}
        with patch.object(sys, 'argv', ['helper', 'FlClash']), \
             patch.object(focus, 'matching_trays', return_value=[(':1.20', '/tray', 7)]), \
             patch.object(focus, 'show_flclash') as show, \
             patch.object(focus, 'run', side_effect=[json.dumps([window]), '']):
            self.assertEqual(focus.main(), 0)
            show.assert_not_called()

    def test_other_missing_app_retains_original_fallback(self):
        with patch.object(sys, 'argv', ['helper', 'OtherApp']), \
             patch.object(focus, 'matching_trays', return_value=[]), \
             patch.object(focus, 'show_flclash') as show, \
             patch.object(focus, 'run', return_value='[]'):
            self.assertEqual(focus.main(), 1)
            show.assert_not_called()


if __name__ == '__main__':
    unittest.main()
