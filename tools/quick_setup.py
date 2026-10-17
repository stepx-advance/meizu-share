# SPDX-License-Identifier: MIT
"""Interactive USB setup; does not download dependencies or select other models."""
import argparse
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import device


def find_adb(explicit=None):
    return device.find_adb(explicit)


def choose_target(adb):
    result = device.execute([adb, "devices"])
    targets = []
    unauthorized = False
    no_permissions = False
    offline = False
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 2:
            continue
        serial, status = fields[:2]
        if "no permissions" in line:
            no_permissions = True
            continue
        if status == "offline":
            offline = True
        if status == "unauthorized":
            unauthorized = True
        if status != "device":
            continue
        model = device.execute([adb, "-s", serial, "shell", "getprop", "ro.product.model"]).stdout.strip()
        if model == "PZ261A":
            targets.append(serial)
    if not targets:
        if no_permissions and sys.platform.startswith("linux"):
            raise RuntimeError("Linux USB 权限不足。请按 README 配置 udev 规则及用户组，重新登录并插拔手机后再试。")
        message = "没有检测到已允许调试的 PZ261A。请用 USB 连接并解锁手机，打开 USB 调试。"
        if unauthorized:
            message += "电脑已检测到待授权设备，请在手机上允许此电脑调试。"
        if offline:
            message += "设备处于离线状态，请重新连接并检查手机上的调试授权。"
        raise RuntimeError(message)
    if len(targets) == 1:
        print("已选择唯一的 PZ261A；其他型号设备不参与安装。")
        return targets[0]
    raise RuntimeError("连接了多台 PZ261A。请只保留要配置的一台，或使用 --target 明确指定。")


def main():
    if sys.version_info < (3, 9):
        raise RuntimeError("需要 Python 3.9 或更高版本。")
    parser = argparse.ArgumentParser(description="PZ261A 互传快捷安装向导")
    parser.add_argument("--adb")
    parser.add_argument("--target")
    parser.add_argument("--dry-run", action="store_true", help="只校验安装包与手机，不写入")
    parser.add_argument("--state", type=Path, default=device.ROOT / ".local-state/setup.json")
    parser.add_argument("--engine-only", action="store_true", default=not (device.ROOT / "dist/share-bridge.apk").is_file(), help="仅安装原厂互传，不提供额外桌面图标或控制中心按钮")
    args = parser.parse_args()
    adb = find_adb(args.adb)
    target = device.Device(args.target or choose_target(adb), adb)
    before, bundle = device.prepare(target, engine_only=args.engine_only)
    print("安装包和系统保护检查通过。")
    for package, _, _ in bundle:
        print(package + ("：复用已有版本" if target.paths(package) else "：新安装"))
    if args.dry_run:
        print("仅检查完成，没有安装、授权或修改手机配置。")
        return
    if args.state.exists():
        raise RuntimeError("本地已有安装状态，未重复安装。请先按说明复核或回滚，保留原状态文件。")
    print("开始安装和授权。若手机显示 USB 安装确认，请及时接受。")
    device.configure(target, SimpleNamespace(state=args.state, engine_only=args.engine_only))
    input("请在手机完成首次确认，打开蓝牙、WLAN 和互传。完成后按回车进入通知设置。")
    device.guide(target, "notifications")
    if args.engine_only:
        print("请开启该应用的通知、悬浮通知和实况通知。仅原厂模式不添加桌面图标或控制中心按钮。")
        print("发送文件时，在系统分享面板选择互传。再次打开设置可执行 tools/device.py guide --target DEVICE_ID。")
    else:
        input("请开启该应用的通知、悬浮通知和实况通知。完成后按回车打开控制中心。")
        device.guide(target, "tiles")
        print("在控制中心点编辑 → 添加，找到“互传”并添加；长按按钮可打开互传设置。")
    print("请从另一台手机发一个小文件，确认发现、接收提示和传输；再反向发送测试。")
    print("首次状态保存在 .local-state/，请本地保留，分享安装包时不要附带此目录。")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, EOFError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
