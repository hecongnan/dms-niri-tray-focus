#!/usr/bin/env python3
"""Install or roll back the DMS 1.6.2 niri tray focus patch without sudo."""
import argparse
import datetime
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

NAME = 'dms-niri-tray-focus'
DROPIN = '99-niri-tray-focus.conf'


def environment(name, value):
    value = str(value)
    if '\n' in value or '\r' in value:
        raise ValueError('Paths must not contain newlines')
    value = value.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"')
    return f'Environment="{name}={value}"\n'


def source_root(source):
    root = Path(source).expanduser().resolve()
    if (root / 'quickshell/shell.qml').is_file():
        root = root / 'quickshell'
    if not (root / 'shell.qml').is_file() or not (root / 'DankCommon').is_dir():
        raise ValueError('Source must contain shell.qml and resolved DankCommon/ dependencies')
    if (root / 'VERSION').read_text().strip().removeprefix('v') != '1.6.2':
        raise ValueError('This patch is tested only with DMS 1.6.2')
    return root


def install(source, data_home, config_home):
    kit = Path(__file__).resolve().parent
    target = data_home / NAME
    dropin = config_home / 'systemd/user/dms.service.d' / DROPIN
    if target.exists() or dropin.exists():
        raise ValueError('An installation already exists; run uninstall before reinstalling')
    root = source_root(source)
    if root == target or root in target.parents:
        raise ValueError('Installation destination must be outside the source tree')
    for tool in ('patch', 'niri', 'busctl'):
        if not shutil.which(tool):
            raise ValueError(f'Missing dependency: {tool}')
    data_home.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.dms-tray-stage-', dir=data_home) as temp:
        stage = Path(temp) / 'shell'
        # Dereference the upstream DankCommon symlink so the copy is self-contained.
        shutil.copytree(root, stage, symlinks=False)
        for directory in [stage] + [p for p in stage.rglob('*') if p.is_dir()]:
            directory.chmod(directory.stat().st_mode | 0o700)
        qml = stage / 'Modules/DankBar/Widgets/SystemTrayBar.qml'
        qml.chmod(qml.stat().st_mode | 0o200)
        patch = kit / 'tray-focus.patch'
        args = ['patch', '--batch', '--fuzz=0', '-p1', '-i', str(patch)]
        subprocess.run(args + ['--dry-run'], cwd=stage, check=True)
        subprocess.run(args, cwd=stage, check=True)
        text = qml.read_text()
        if text.count('root.activateOrFocusTrayItem(') != 4:
            raise ValueError('Unexpected tray activation call sites; patch not installed')
        shutil.copy2(kit / 'focus-tray-window.py', stage)
        wrapper = stage / 'focus-tray-window'
        wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                           shlex.quote(str(target / 'focus-tray-window.py')) + ' "$@"\n')
        wrapper.chmod(0o755)
        content = '[Service]\n' + environment('DMS_SHELL_DIR', target) + environment(
            'DMS_TRAY_FOCUS_HELPER', target / 'focus-tray-window')
        dropin.parent.mkdir(parents=True, exist_ok=True)
        stage.rename(target)
        try:
            with dropin.open('x') as stream:
                stream.write(content)
        except Exception:
            shutil.rmtree(target)
            raise
    print(f'Installed: {target}\nService override: {dropin}')


def uninstall(data_home, config_home):
    target = data_home / NAME
    dropin = config_home / 'systemd/user/dms.service.d' / DROPIN
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    # Keep recoverable copies, and leave every other DMS drop-in untouched.
    for path in (dropin, target):
        if path.exists():
            backup = path.with_name(path.name + '.disabled-' + stamp)
            path.rename(backup)
            print(f'Preserved: {backup}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall'])
    parser.add_argument('--source', help='DMS UI directory or source checkout')
    parser.add_argument('--data-home', type=Path, default=Path(os.environ.get(
        'XDG_DATA_HOME', str(Path.home() / '.local/share'))))
    parser.add_argument('--config-home', type=Path, default=Path(os.environ.get(
        'XDG_CONFIG_HOME', str(Path.home() / '.config'))))
    parser.add_argument('--restart', action='store_true', help='Reload and restart dms.service')
    args = parser.parse_args()
    if args.action == 'install':
        source = args.source
        if not source:
            runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
            source = (runtime / 'danklinux.path').read_text().strip()
        install(source, args.data_home.expanduser().resolve(), args.config_home.expanduser().resolve())
    else:
        uninstall(args.data_home.expanduser().resolve(), args.config_home.expanduser().resolve())
    if args.restart:
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'restart', 'dms.service'], check=True)
    else:
        print('To activate: systemctl --user daemon-reload && systemctl --user restart dms.service')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
