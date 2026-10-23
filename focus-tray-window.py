import json
import subprocess
import sys
import time


def run(*args):
    return subprocess.check_output(args, text=True, timeout=2)


def normalize(value):
    return (value or '').lower().removesuffix('.desktop')


def choose_window(windows, identities, pids):
    # PID handles generic Chromium tray IDs; exact app IDs handle tray helpers.
    candidates = [w for w in windows if w.get('pid') in pids]
    if not candidates:
        candidates = [w for w in windows if normalize(w.get('app_id')) in identities]
    if not candidates:
        return None
    def recent(w):
        stamp = w.get('focus_timestamp') or {}
        return (stamp.get('secs', 0), stamp.get('nanos', 0))
    return max(candidates, key=recent)


def matching_trays(tray_id):
    items = json.loads(run('busctl', '--user', '--json=short', 'get-property',
        'org.kde.StatusNotifierWatcher', '/StatusNotifierWatcher',
        'org.kde.StatusNotifierWatcher', 'RegisteredStatusNotifierItems'))['data']
    matches = []
    for item in items:
        bus, _, path = item.partition('/')
        try:
            data = json.loads(run('busctl', '--user', '--json=short', 'get-property',
                bus, '/' + path, 'org.kde.StatusNotifierItem', 'Id'))['data']
            if data != tray_id:
                continue
            pid = json.loads(run('busctl', '--user', '--json=short', 'call',
                'org.freedesktop.DBus', '/org/freedesktop/DBus',
                'org.freedesktop.DBus', 'GetConnectionUnixProcessID', 's', bus))['data'][0]
            matches.append((bus, '/' + path, pid))
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            continue
    return matches


def show_menu_entry(layout):
    # Only accept an explicit, enabled, non-toggle Show action. Never guess the
    # first item: FlClash also exposes proxy/TUN toggles and Quit in this menu.
    for variant in layout[2]:
        entry_id, properties, children = variant['data']
        label = properties.get('label', {}).get('data', '')
        label = label.replace('_', '').replace('&', '').strip().casefold()
        if (label in {'show', '显示', '顯示'} and not children
                and 'toggle-type' not in properties
                and properties.get('enabled', {}).get('data', True)
                and properties.get('visible', {}).get('data', True)):
            return entry_id
    return None


def show_flclash(bus, object_path):
    menu = json.loads(run('busctl', '--user', '--json=short', 'get-property',
        bus, object_path, 'org.kde.StatusNotifierItem', 'Menu'))['data']
    data = json.loads(run('busctl', '--user', '--json=short', 'call',
        bus, menu, 'com.canonical.dbusmenu', 'GetLayout', 'iias', '0', '1', '0'))['data']
    entry = show_menu_entry(data[1])
    if entry is None:
        return False
    run('busctl', '--user', 'call', bus, menu, 'com.canonical.dbusmenu',
        'Event', 'isvu', str(entry), 'clicked', 'i', '0', '0')
    return True


def main():
    tray_id = sys.argv[1]
    identities = {normalize(tray_id)} - {''}
    windows = json.loads(run('niri', 'msg', '-j', 'windows'))
    window = choose_window(windows, identities, set())
    if window is None:
        trays = matching_trays(tray_id)
        pids = {pid for _, _, pid in trays}
        window = choose_window(windows, identities, pids)
        # FlClash's Ayatana tray has no Activate method. A closed/hidden Flutter
        # window is absent from niri's list, so restore it through its Show menu.
        if window is None and normalize(tray_id) == 'flclash':
            for bus, object_path, _ in trays:
                if show_flclash(bus, object_path):
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        windows = json.loads(run('niri', 'msg', '-j', 'windows'))
                        window = choose_window(windows, identities, pids)
                        if window is not None:
                            break
                        time.sleep(0.1)
                    break
    if window is None:
        return 1
    run('niri', 'msg', 'action', 'focus-window', '--id', str(window['id']))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        sys.exit(1)
