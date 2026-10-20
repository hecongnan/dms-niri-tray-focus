# DMS + niri：托盘点击聚焦补丁

Standalone tray focus patch for **DankMaterialShell 1.6.2 + niri**.
独立于个人 NixOS 配置，不需要 sudo。克隆此公开仓库或下载源码压缩包即可使用。

```sh
git clone https://github.com/hecongnan/dms-niri-tray-focus.git
cd dms-niri-tray-focus
```

## 行为

- 左键点击普通应用托盘：已有窗口就聚焦；多个窗口选择最近使用的窗口。
- 优先精确匹配托盘 Id 与窗口 app_id；通用 Chromium 托盘 Id 则通过会话 D-Bus 匹配 PID。
- 没有匹配、查询失败时回退到应用原来的 Activate 行为。
- 保留菜单型托盘、右键菜单、拖动和其他合成器的行为。
- 覆盖四处托盘点击路径；不修改 DMS 的 `tray activate` IPC 接口。

## 安装

依赖：Python **3.9+**、GNU patch、niri、systemd 的 `busctl`。
自动安装器适用于以用户级 **dms.service** 运行的 DMS 1.6.2。
先启动一次 DMS，然后在补丁目录执行：

```sh
python3 install.py install --restart
```

安装器从 `$XDG_RUNTIME_DIR/danklinux.path` 读取当前 DMS 界面路径。
也可以明确指定含 `shell.qml`、`VERSION`、完整 `DankCommon/` 的界面目录，
或已补齐 DankCommon 依赖的 DMS 源码 checkout：

```sh
python3 install.py install --source /path/to/DankMaterialShell --restart
```

去掉 `--restart` 只安装文件，稍后自行重启服务。安装器复制界面并对副本应用补丁，
不改原始源码或 `/nix/store`。若副本/覆盖文件已存在则拒绝覆盖。

默认安装位置：

- `$XDG_DATA_HOME/dms-niri-tray-focus/`（默认 `~/.local/share/`）
- `$XDG_CONFIG_HOME/systemd/user/dms.service.d/99-niri-tray-focus.conf`（默认 `~/.config/`）

## 验证

```sh
systemctl --user is-active dms.service
systemctl --user show dms.service -p Environment
journalctl --user -u dms.service -n 50 --no-pager
```

确认 `DMS_SHELL_DIR` 指向上述副本。在其他工作区打开应用，切换离开后点击其托盘，
应回到已有窗口。没有窗口时保留该应用原有托盘行为，不保证应用一定创建窗口。

## 回滚

```sh
python3 install.py uninstall --restart
```

只把本补丁创建的界面副本和 `99-niri-tray-focus.conf` 重命名为 `.disabled-时间戳`，
保留可恢复副本；不改其他覆盖配置。如果原来已有其他 `DMS_SHELL_DIR` 覆盖，
回滚后会重新使用它，而不是强制恢复上游界面。

## 手动 patch / 非 systemd 启动

对 **DMS 1.6.2** 的界面目录副本执行（源码 checkout 中通常是 `quickshell/`）：

```sh
cd /path/to/ui-copy
patch --batch --fuzz=0 --dry-run -p1 < /path/to/kit/tray-focus.patch
patch --batch --fuzz=0 -p1 < /path/to/kit/tray-focus.patch
```

将 `focus-tray-window.py` 放到固定路径，创建可执行包装脚本：

```sh
#!/bin/sh
exec python3 /absolute/path/focus-tray-window.py "$@"
```

启动 DMS 时传入两个环境变量：

```sh
DMS_SHELL_DIR=/absolute/path/ui-copy \
DMS_TRAY_FOCUS_HELPER=/absolute/path/executable-wrapper dms run
```

## 限制与升级

- 只验证过 DMS **1.6.2**，安装器会拒绝其他版本。升级时需重新适配补丁并安装；
  本地界面副本不会随 DMS 软件包自动升级。
- 自定义 app_id、托盘由独立辅助进程承载、多个实例使用相同托盘 Id 等情况可能无法准确区分；
  无法匹配时保留原始激活行为。不使用窗口标题模糊匹配，以减少误聚焦。
- 本机已验证微信和 ChatGPT 的已有窗口聚焦，详见 [验证记录](VERIFICATION.md)。
- NixOS 用户可使用此独立安装器；不要修改 `/nix/store` 中的源码。

## 许可

MIT；补丁中的上游上下文来自 [DankMaterialShell](https://github.com/AvengeMedia/DankMaterialShell)，保留其版权声明。
