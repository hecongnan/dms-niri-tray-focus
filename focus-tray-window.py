import json
import subprocess
import sys


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


def main():
    tray_id = sys.argv[1]
    windows = json.loads(run('niri', 'msg', '-j', 'windows'))
    identities = {normalize(tray_id)} - {''}
    # Skip D-Bus lookup when the tray ID is already an exact app ID.
    window = choose_window(windows, identities, set())
    if window is None:
        items = json.loads(run('busctl', '--user', '--json=short', 'get-property',
            'org.kde.StatusNotifierWatcher', '/StatusNotifierWatcher',
            'org.kde.StatusNotifierWatcher', 'RegisteredStatusNotifierItems'))['data']
        pids = set()
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
                pids.add(pid)
            except (subprocess.SubprocessError, ValueError, KeyError):
                continue
        window = choose_window(windows, identities, pids)
    if window is None:
        return 1
    run('niri', 'msg', 'action', 'focus-window', '--id', str(window['id']))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        sys.exit(1)
