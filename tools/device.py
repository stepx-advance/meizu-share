# SPDX-License-Identifier: MIT
"""Install the bundled original engine and independent entry application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE = "com.meizu.share"
BRIDGE = "local.pz261a.shareentry"
TILE = BRIDGE + "/.ShareTileService"
ENGINE_HASH = "4f4fa92b4000d371c33f4319f49fd25a8f7caece9c1bcce4136d953da5a2b756"
ENGINE_PERMISSIONS = [
    "android.permission.WRITE_SECURE_SETTINGS", "android.permission.BLUETOOTH_SCAN",
    "android.permission.BLUETOOTH_CONNECT", "android.permission.BLUETOOTH_ADVERTISE",
    "android.permission.NEARBY_WIFI_DEVICES", "android.permission.POST_NOTIFICATIONS",
]
BRIDGE_PERMISSIONS = ["android.permission.WRITE_SECURE_SETTINGS", "android.permission.BLUETOOTH_CONNECT"]
RESERVED_PACKAGES = ["com.stepos.share"]
RESERVED_ACTIONS = ["stepos.intent.action.stepos_share"]
KNOWN_SYSTEM_HASHES = {
    "/system_ext/priv-app/Settings/Settings.apk": "eb75ed980cd725518b421536d1c53a27c455eb0f8fd2158ce0a44c7cf24a7e90",
    "/system_ext/priv-app/ConnectivitySettings/ConnectivitySettings.apk": "b61158d4ed190141b88a66450d795eec09083ede233cd6b0d5cf0f9714c9510d",
    "/system_ext/priv-app/SystemUI/SystemUI.apk": "256fe8ea05811f9a1d31ae133efac4b8d98589dc34d09ef4ec94ecdd3502edcc",
    "/system_ext/priv-app/DSoftBusService/DSoftBusService.apk": "c009c6bc8343991a5565010a3a31b7bbf6fa5164494066e7ef319c2a1a5b20ca",
    "/system_ext/framework/stepos-framework.jar": "89a55db17240730abeaa16d812d67f9e7c03b013d9e53dd1460811c463105138",
    "/system_ext/framework/stepos-services.jar": "488f32dd32462d307e8d41fb99a935ea00135ed4b007c050841fe83ac8fe9aa5",
    "/system/framework/framework.jar": "be8c46f21fd2866b9908dd80d52a4bd7b3949f53d379897c6bdb41ae34d928bb",
    "/system/framework/services.jar": "bfd925847906475a512c0b7bdec616ae955617a2a4f9cc0a2f7892f1b38b6cb1",
}
SYSTEM_FILES = list(KNOWN_SYSTEM_HASHES)


def find_adb(explicit=None):
    if explicit:
        found = shutil.which(str(Path(explicit).expanduser()))
        if found:
            return found
        raise RuntimeError("指定的 adb 不存在或不可执行；请检查路径、执行权限和主机架构。")
    found = shutil.which("adb")
    if found:
        return found
    suffix = "adb.exe" if os.name == "nt" else "adb"
    candidates = []
    for key in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        if os.environ.get(key):
            candidates.append(Path(os.environ[key]) / "platform-tools" / suffix)
    candidates.append(ROOT / "platform-tools" / suffix)
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library/Android/sdk/platform-tools" / suffix)
    candidates.extend([Path.home() / "Android/Sdk/platform-tools" / suffix,
                       Path.home() / "Android/sdk/platform-tools" / suffix])
    if sys.platform.startswith("linux"):
        candidates.extend([Path.home() / ".local/share/android-sdk/platform-tools" / suffix,
                           Path("/usr/lib/android-sdk/platform-tools") / suffix,
                           Path("/opt/android-sdk/platform-tools") / suffix])
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk/platform-tools" / suffix)
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise RuntimeError("找不到 Android platform-tools。请安装后将 adb 加入 PATH，或使用 --adb 指定。")


def execute(args, check=True):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if check and r.returncode:
        raise RuntimeError((r.stderr or r.stdout or "Command failed").strip())
    return r


class Device:
    def __init__(self, serial, adb=None):
        self.serial = serial
        self.adb = find_adb(adb)
        if not self.adb:
            raise RuntimeError("找不到 adb；请将 Android platform-tools 加入 PATH，或使用 --adb。")
        if execute([self.adb, "-s", serial, "get-state"]).stdout.strip() != "device":
            raise RuntimeError("目标设备未就绪。")

    def sh(self, *args, check=True):
        return execute([self.adb, "-s", self.serial, "shell", shlex.join(args)], check=check).stdout.strip()

    def paths(self, package):
        return [x[8:] for x in self.sh("pm", "path", package, check=False).splitlines() if x.startswith("package:")]

    def apk_hash(self, package):
        paths = self.paths(package)
        if len(paths) != 1:
            return None
        result = self.sh("sha256sum", paths[0], check=False)
        return result.split()[0] if re.match(r"^[0-9a-f]{64} ", result) else None

    def install(self, path):
        execute([self.adb, "-s", self.serial, "install", "--no-incremental", str(path)])

    def uninstall(self, package):
        execute([self.adb, "-s", self.serial, "uninstall", package])

    def appop(self, package, operation):
        result = self.sh("cmd", "appops", "get", "--user", "0", package, operation)
        match = re.search(r"Uid mode:\s*" + re.escape(operation) + r": (allow|ignore|deny|default|foreground)\b", result)
        if match:
            return match.group(1)
        if result == "No operations." or re.search(re.escape(operation) + r": (allow|ignore|deny|default|foreground)\b", result):
            return "default"
        raise RuntimeError("无法确认单应用特殊访问状态，停止配置。")

    def setting(self, namespace, key):
        return self.sh("settings", "get", namespace, key)

    def snapshot(self):
        hashes = {}
        for line in self.sh("sha256sum", *SYSTEM_FILES).splitlines():
            digest, name = line.split(None, 1)
            hashes[name.strip()] = digest
        native_services = self.sh("dumpsys", "activity", "services", ENGINE)
        return {
            "schema": 2,
            "current_user": self.sh("am", "get-current-user"),
            "model": self.sh("getprop", "ro.product.model"),
            "android_sdk": self.sh("getprop", "ro.build.version.sdk"),
            "system_version": self.sh("getprop", "ro.build.aios_version"),
            "android_build_id": self.sh("getprop", "ro.build.display.id"),
            "boot_locked": self.sh("getprop", "ro.boot.flash.locked"),
            "verified_boot": self.sh("getprop", "ro.boot.verifiedbootstate"),
            "system_files_sha256": hashes,
            "reserved_packages_present": {p: bool(self.paths(p)) for p in RESERVED_PACKAGES},
            "reserved_actions": {a: self.sh("cmd", "package", "query-activities", "--brief", "-a", a) for a in RESERVED_ACTIONS},
            "stepos_share_provider": self.setting("global", "stepos_share_provider"),
            "dsoftbus_normal_query": self.sh("cmd", "package", "query-services", "--brief", "-a", "com.dsoftbus.START_SERVICE"),
            "engine_apk_sha256": self.apk_hash(ENGINE),
            "bridge_apk_sha256": self.apk_hash(BRIDGE),
            "engine_installed": bool(self.paths(ENGINE)),
            "bridge_installed": bool(self.paths(BRIDGE)),
            "engine_disabled": ("package:" + ENGINE) in self.sh("pm", "list", "packages", "-d", ENGINE).splitlines(),
            "bridge_disabled": ("package:" + BRIDGE) in self.sh("pm", "list", "packages", "-d", BRIDGE).splitlines(),
            "native_share_enabled": self.setting("global", "meizu_share_provider"),
            "native_ble_service_running": ".service.BleGattServerService" in native_services,
        }


def compare(before, after):
    keys = ["system_files_sha256", "stepos_share_provider", "dsoftbus_normal_query"]
    result = {key: before[key] == after[key] for key in keys}
    for field, selected in [("reserved_packages_present", RESERVED_PACKAGES), ("reserved_actions", RESERVED_ACTIONS)]:
        result[field] = all(key in before[field] and key in after[field] and before[field][key] == after[field][key]
                            for key in selected)
    return result


def preflight(snapshot, allow_missing_engine=False, use_bridge=True):
    errors = []
    if snapshot["current_user"] != "0":
        errors.append("只配置已验证的主用户；请切回主用户再检查。")
    if snapshot["model"] != "PZ261A" or snapshot["android_sdk"] != "36":
        errors.append("只接受已验证的 PZ261A / Android 16；其他设备需要单独验证。")
    if snapshot["system_version"] != "Step AOS 1.0.0.2.26001_stable_user_20261004_131555":
        errors.append("系统版本不同于已验证版本，请先重新审计。")
    if snapshot["boot_locked"] != "1" or snapshot["verified_boot"] != "green":
        errors.append("启动校验状态与已验证环境不同，请先重新审计。")
    if snapshot["system_files_sha256"] != KNOWN_SYSTEM_HASHES:
        errors.append("关键系统文件摘要与已验证基线不同，请先重新审计。")
    if snapshot["reserved_packages_present"]["com.stepos.share"]:
        errors.append("已检测到系统互传包，停止配置以避免两套互传同时工作。")
    if any(snapshot["reserved_packages_present"].values()):
        errors.append("系统互传组件状态与已验证基线不同，停止配置，避免影响已有功能。")
    if any(value != "No activities found" for value in snapshot["reserved_actions"].values()):
        errors.append("系统预留动作已有处理组件，停止配置并重新审计。")
    if snapshot["stepos_share_provider"] != "null":
        errors.append("系统预留互传开关键已被使用，停止配置并重新审计。")
    if snapshot["engine_apk_sha256"] != ENGINE_HASH and not (allow_missing_engine and not snapshot["engine_installed"]):
        errors.append("已安装的原厂互传不是已验证版本；停止配置，不覆盖它。")
    if snapshot["engine_disabled"] or (use_bridge and snapshot["bridge_disabled"]):
        errors.append("互传或助手已被使用者停用；请先确认是否需要在系统应用设置中启用。")
    if snapshot["dsoftbus_normal_query"] != "No services found":
        errors.append("DSoftBus 状态与已验证基线不同，停止配置。")
    return errors


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def granted(device, package, permission):
    data = device.sh("dumpsys", "package", package)
    return bool(re.search(re.escape(permission) + r": granted=true\b", data))


def load_bundle(include_bridge=True):
    engine = ROOT / "third_party" / "meizu" / "mzshare-6.1.14.apk"
    if hashlib.sha256(engine.read_bytes()).hexdigest() != ENGINE_HASH:
        raise RuntimeError("原厂互传 APK 校验失败，尚未开始安装。")
    bundle = [(ENGINE, engine, ENGINE_HASH)]
    if include_bridge:
        manifest = json.loads((ROOT / "dist" / "artifacts.json").read_text(encoding="utf-8"))
        bridge = ROOT / "dist" / "share-bridge.apk"
        expected = manifest["bridge_sha256"]
        if hashlib.sha256(bridge.read_bytes()).hexdigest() != expected:
            raise RuntimeError("助手 APK 校验失败，尚未开始安装。")
        bundle.append((BRIDGE, bridge, expected))
    return bundle


def prepare(device, engine_only=False):
    bundle = load_bundle(include_bridge=not engine_only)
    if engine_only:
        bundle = [item for item in bundle if item[0] == ENGINE]
    before = device.snapshot()
    errors = preflight(before, allow_missing_engine=True, use_bridge=not engine_only)
    if not engine_only:
        expected = bundle[1][2]
        accepted = [expected, "f814d72231e0ccc1b47dfc190f09c1d60a3ad9c23d28a408d2fb2a7facf49c85"]
        if before["bridge_installed"] and before["bridge_apk_sha256"] not in accepted:
            errors.append("助手包名已被其他版本占用；不会替换或卸载该应用。")
    if errors:
        raise RuntimeError("\n".join(errors))
    return before, bundle


def configure(device, args):
    if args.state.exists():
        raise RuntimeError("状态文件已存在；为保留原始回滚基线，拒绝覆盖。")
    engine_only = getattr(args, "engine_only", False)
    before, bundle = prepare(device, engine_only=engine_only)
    state = {"schema": 2, "target_tag": hashlib.sha256(device.serial.encode()).hexdigest(), "before": before,
             "engine_only": engine_only, "permission_targets_sha256": {ENGINE: ENGINE_HASH},
             "granted": [], "settings": [], "appops": [], "installs": [], "complete": False}
    if not engine_only:
        state["permission_targets_sha256"][BRIDGE] = before["bridge_apk_sha256"] or bundle[1][2]
    save(args.state, state)
    for package, apk, digest in bundle:
        if not device.paths(package):
            item = {"package": package, "sha256": digest, "status": "pending"}
            state["installs"].append(item)
            save(args.state, state)
            print("正在安装：" + ("魅族互传" if package == ENGINE else "互传快捷入口") + "；请留意手机上的安装确认。")
            device.install(apk)
            if device.apk_hash(package) != digest:
                raise RuntimeError("安装后 APK 校验失败；已保留状态供回滚。")
            item["status"] = "installed"
            save(args.state, state)
    permission_targets = [(ENGINE, ENGINE_PERMISSIONS)]
    if not engine_only:
        permission_targets.append((BRIDGE, BRIDGE_PERMISSIONS))
    for package, permissions in permission_targets:
        for permission in permissions:
            if not granted(device, package, permission):
                state["granted"].append([package, permission])
                save(args.state, state)
                device.sh("pm", "grant", "--user", "0", package, permission)
                if not granted(device, package, permission):
                    raise RuntimeError("单应用授权未生效；已保留状态供回滚。")
    old_mode = device.appop(ENGINE, "MANAGE_EXTERNAL_STORAGE")
    if old_mode != "allow":
        state["appops"].append({"package": ENGINE, "op": "MANAGE_EXTERNAL_STORAGE", "scope": "uid", "before": old_mode, "after": "allow"})
        save(args.state, state)
        device.sh("cmd", "appops", "set", "--user", "0", "--uid", ENGINE, "MANAGE_EXTERNAL_STORAGE", "allow")
        if device.appop(ENGINE, "MANAGE_EXTERNAL_STORAGE") != "allow":
            raise RuntimeError("所有文件访问未生效；已保留状态供回滚。")
    old_name = device.setting("global", "meizu_share_device_name")
    if old_name in ("", "null"):
        change = {"namespace": "global", "key": "meizu_share_device_name", "before": old_name, "after": "PZ261A"}
        state["settings"].append(change)
        save(args.state, state)
        device.sh("settings", "put", "global", "meizu_share_device_name", "PZ261A")
    guide(device, "native")
    state["after"] = device.snapshot()
    state["protected_checks"] = compare(before, state["after"])
    state["complete"] = all(state["protected_checks"].values())
    save(args.state, state)
    if not state["complete"]:
        raise RuntimeError("保护项出现变化，状态已记录；停止后续操作并检查状态文件。")
    print("安装和基础配置完成。请在手机中完成原厂首次确认，打开蓝牙、WLAN 和互传。")
    print("接下来开启该应用的悬浮和实况通知。")
    if not engine_only:
        print("通过控制中心编辑页添加“互传”。")


def rollback(device, args):
    state = json.loads(args.state.read_text(encoding="utf-8"))
    if state.get("rolled_back"):
        raise RuntimeError("该状态已执行过回滚；拒绝重复撤销之后可能重新授予的权限。")
    if state["target_tag"] != hashlib.sha256(device.serial.encode()).hexdigest():
        raise RuntimeError("状态文件不属于当前设备，拒绝回滚。")
    if state.get("schema") != 2:
        raise RuntimeError("请使用生成该状态文件的对应版本工具回滚。")
    permission_targets = state["permission_targets_sha256"]
    unchanged = {package: device.apk_hash(package) == digest for package, digest in permission_targets.items()}
    if unchanged.get(ENGINE) and (any(package == ENGINE for package, _ in state["granted"]) or
                                  any(change["package"] == ENGINE for change in state["appops"])):
        device.sh("am", "force-stop", ENGINE)
    for change in reversed(state["appops"]):
        package, operation = change["package"], change["op"]
        if unchanged.get(package) and device.appop(package, operation) == change["after"]:
            device.sh("cmd", "appops", "set", "--user", "0", "--uid", package, operation, change["before"])
    for change in reversed(state["settings"]):
        ns, key = change["namespace"], change["key"]
        if device.setting(ns, key) != change["after"]:
            print("保留后来修改的配置：" + key)
            continue
        if change["before"] == "null":
            device.sh("settings", "delete", ns, key)
        else:
            device.sh("settings", "put", ns, key, change["before"])
    for package, permission in reversed(state["granted"]):
        if unchanged.get(package):
            device.sh("pm", "revoke", "--user", "0", package, permission)
        else:
            print("应用已移除或被替换，保留其当前权限：" + package)
    for item in reversed(state["installs"]):
        package = item["package"]
        if package == ENGINE and not getattr(args, "remove_engine", False):
            continue
        if device.apk_hash(package) == item["sha256"]:
            if package == BRIDGE:
                device.sh("cmd", "statusbar", "remove-tile", TILE, check=False)
            device.uninstall(package)
        elif device.paths(package):
            print("应用已被后来替换，保留该应用：" + package)
    state["rolled_back"] = True
    save(args.state, state)
    print("已回滚工具直接记录的改动；共享下载文件及手动通知设置不由工具清理。")


def guide(device, page):
    if page == "notifications":
        device.sh("am", "start", "-a", "android.settings.APP_NOTIFICATION_SETTINGS", "--es", "android.provider.extra.APP_PACKAGE", ENGINE)
    elif page == "files":
        device.sh("am", "start", "-a", "android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION", "-d", "package:" + ENGINE)
    elif page == "tiles":
        device.sh("cmd", "statusbar", "expand-settings")
    else:
        device.sh("am", "start", "-n", ENGINE + "/.mutual.MutualSettingsActivity")


def main():
    parser = argparse.ArgumentParser(description="PZ261A 互传助手：检查、配置、回滚")
    parser.add_argument("command", choices=["audit", "install", "configure", "check", "guide", "rollback"])
    parser.add_argument("--target", required=True, help="adb 设备标识；仅用于选择设备")
    parser.add_argument("--adb", help="adb 程序路径")
    parser.add_argument("--output", type=Path, help="检查报告输出位置；报告不含设备标识")
    parser.add_argument("--baseline", type=Path, help="可选的先前检查报告")
    parser.add_argument("--state", type=Path, default=ROOT / ".local-state" / "setup.json")
    parser.add_argument("--engine-only", action="store_true", default=not (ROOT / "dist/share-bridge.apk").is_file(), help="仅安装配置原厂互传，不安装、授权或更改快捷入口")
    parser.add_argument("--page", choices=["native", "notifications", "files", "tiles"], default="native")
    parser.add_argument("--remove-engine", action="store_true", help="回滚时也卸载本工具新安装且内容未变的原厂互传；会删除该应用的私有数据")
    args = parser.parse_args()
    device = Device(args.target, args.adb)
    if args.command == "audit":
        result = device.snapshot()
        if args.baseline:
            result["protected_checks"] = compare(json.loads(args.baseline.read_text(encoding="utf-8")), result)
        if args.output:
            save(args.output, result)
            print("检查报告已保存。")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "check":
        before, bundle = prepare(device, engine_only=args.engine_only)
        print("安装包、系统文件与预留保护检查通过；没有执行写入。")
        for package, _, _ in bundle:
            print(package + ("：复用现有版本" if device.paths(package) else "：准备新安装"))
    elif args.command in ("configure", "install"):
        configure(device, args)
    elif args.command == "guide":
        guide(device, args.page)
    else:
        rollback(device, args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
