# 验证记录

环境：DMS 1.6.2；niri；Python 3.13。此补丁包只声明支持 DMS 1.6.2。

已验证：

- 上游 DMS 1.6.2 的 SystemTrayBar.qml 能以 `patch --fuzz=0` 应用补丁。
- 四处普通托盘点击调用都进入聚焦逻辑。
- 已运行环境中的微信 app_id 匹配与 ChatGPT D-Bus PID 匹配。
- 多窗口最近聚焦选择，无匹配时返回失败供界面执行原始 Activate。
- 独立安装器在隔离目录中，使用只读上游文件和带空格的安装路径安装成功。
- 原始上游文件内容保持一致，生成的脚本包装器可执行。
- 已有安装拒绝覆盖。
- 卸载保留可恢复副本，并保留其他 systemd drop-in。
- Python 语法检查及安装器 `--help`。

未通过此安装器重启实际桌面；当前桌面使用之前已部署的等效补丁。
独立安装器的 systemd 重启流程需要使用者在自己的 DMS 会话中验证。

## 2026-10-23 FlClash 隐藏窗口修复

本机 FlClash 0.8.99 的 Ayatana 托盘仅提供菜单和 SecondaryActivate，未提供 Activate。
隐藏时窗口不在 niri 的窗口列表中；已确认触发 DBusMenu 的“显示”项能恢复
app_id=com.follow.clash 的窗口。脚本新增仅针对 FlClash 的恢复逻辑。

`python3 test_focus.py` 验证动态菜单 ID、隐藏窗口恢复与聚焦、已有窗口直接聚焦、
禁用/隐藏/勾选项排除、其他应用仍使用原始失败回退，共 6 项通过。
