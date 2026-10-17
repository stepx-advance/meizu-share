# meizu-share · STEPX Advance

STEPX Advance 系列的 PZ261A 互传适配工具，支持 Linux、macOS 和 Windows。通过魅族原厂互传进行兼容设备之间的文件收发。

本项目为非官方兼容方案。原厂 APK 保持原签名，不修改系统文件，不占用 STEPX 系统互传预留的包名及入口。

## 下载

从 [Releases](https://github.com/stepx-advance/meizu-share/releases) 下载成品安装包：

- `meizu-share-v0.1.0-minimal.zip`：仅原厂互传。
- `meizu-share-v0.1.0-with-shortcuts.zip`：附带桌面与控制中心入口。
- `SHA256SUMS`：两个安装包的校验值。

仓库保存原创源码、工具和版权说明；原厂 APK 与编译后的入口组件随 Release 安装包提供。

## 安装方案

| 方案 | 手机安装内容 | 使用入口 |
| --- | --- | --- |
| 精简版 | 魅族原厂互传 | 系统分享面板；通过电脑打开设置 |
| 带快捷入口版 | 原厂互传＋约 17 KB 的入口组件 | 增加桌面图标和控制中心开关 |

快捷入口只负责打开设置和控制开关。文件收发、接收通知和顶部胶囊均由原厂互传及系统处理，不依赖入口组件。带快捷入口版可使用 `--engine-only` 仅安装配置原厂互传，已有入口组件会保留。

## 适用环境

- 手机：PZ261A，Android 16。
- 固件：`Step AOS 1.0.0.2.26001_stable_user_20261004_131555`。
- 原厂互传：6.1.14。
- 电脑：Linux、macOS 或 Windows，需要 Python 3.9+ 和 Android platform-tools。

安装器会核对固件、八个关键系统文件和系统互传预留状态。不同机型、固件、未知已安装组件或校验值不匹配时会停止配置。

## 安装

1. 从 [Android 官方下载页](https://developer.android.com/tools/releases/platform-tools) 取得适用本机的 platform-tools，并准备 Python 3.9+。
2. 解压安装包。手机用 USB 连接电脑，解锁、开启 USB 调试，并允许此电脑调试。
3. Linux 执行 `sh ./install.sh`；macOS 双击 `install.command`；Windows 双击 `install.bat`。
4. 按提示处理手机上的安装确认，完成原厂首次设置，打开蓝牙、WLAN 和互传。
5. 开启互传应用的悬浮通知和实况通知。使用带快捷入口版时，在控制中心编辑页面添加“互传”。

工具只自动选择唯一一台已允许调试的 PZ261A；多台目标机同时连接时会停止，可用 `--target DEVICE_ID` 明确选择。已有且校验值匹配的组件会复用，未知版本不会被覆盖。

无需 Root 或 Shizuku。Python、platform-tools、JDK 和 Android SDK 不随安装包分发。

## Linux 使用

安装 Python 3.9+ 和适用于本机的 Android platform-tools，将 `adb` 加入 PATH。工具也会检查 `ANDROID_SDK_ROOT`、`ANDROID_HOME`、用户目录下的 Android SDK 和常用系统 SDK 路径；也可通过 `--adb /path/to/adb` 指定。

在解压目录运行：

```sh
sh ./install.sh
```

只检查、不安装：

```sh
sh ./install.sh --dry-run
```

遇到 USB 权限不足时，Ubuntu 用户可按 [Android 官方设备连接说明](https://developer.android.com/studio/run/device) 安装 udev 规则，并将当前用户加入 `plugdev` 组：

```sh
sudo apt-get install android-sdk-platform-tools-common
sudo usermod -aG plugdev "$(id -un)"
```

完成后重新登录并重新连接手机。其他发行版按其设备权限规则配置。本工具不会自动修改电脑的 udev 规则或用户组。

## 实际改动

- 安装缺少的原厂互传，以及所选方案的入口组件。
- 补齐所选应用必要的附近设备、通知和开发权限。
- 允许原厂互传访问收发所需的存储空间。
- 仅在设备名缺失时填入 `PZ261A`。

原厂应用运行后会产生自身配置和接收文件。通知选项与控制中心布局由使用者在手机上设置。安装器不替换系统应用，不改系统分区，不禁用已有应用，不自动同意原厂隐私条款。

## 常用操作

以下命令可用于 Linux 和 macOS。Windows 可将 `python3` 换为 `py -3`。

```sh
python3 tools/quick_setup.py --dry-run
python3 tools/device.py guide --target DEVICE_ID
python3 tools/device.py guide --target DEVICE_ID --page notifications
```

`DEVICE_ID` 为自己手机在 `adb devices` 中显示的设备标识；找不到 adb 时可追加 `--adb /path/to/adb`。发送文件时，在系统分享面板选择互传。

## 回滚

首次配置状态保存在 `.local-state/`，请本地保留，不要随安装包分享。

```sh
python3 tools/device.py rollback --target DEVICE_ID
```

默认撤销工具记录的新授权和直接配置，移除工具新安装且内容未变的入口组件，保留原厂互传。若还要卸载工具新安装的原厂互传，首次回滚时添加：

```sh
python3 tools/device.py rollback --target DEVICE_ID --remove-engine
```

卸载会清除应用私有数据。工具不清理共享下载文件，不卸载安装前已有的原厂互传，不保证还原原厂自行产生的全部状态。详见 [安装与回滚边界](docs/OPERATIONS.md)。

## 限制

- 尚未加入系统“设置 → 更多连接”入口。
- 对端显示 STEPX 品牌图标尚未实现。
- 其他机型、固件及重启、OTA、长期运行的兼容性需要另行确认。
- Linux 提供启动、依赖检测、安装、检查和回滚支持；Linux USB 连接及 Windows 启动仍待实机确认。

## 源码与版权

本项目原创工具、快捷入口及文档采用 [MIT](LICENSE)。构建入口组件见 [BUILD.md](docs/BUILD.md)。

魅族原厂 APK 及其代码、图片、字体、库等资源的权利属于魅族及各自权利人，不适用本项目 MIT 许可。原厂 APK 未修改、未重签名，内部通知原样保留，见 [NOTICE.txt](third_party/meizu/NOTICE.txt) 和 [版权说明](docs/RIGHTS.md)。

STEPX、Flyme、Meizu 等名称仅用于说明兼容对象，本项目没有相关厂商或互传联盟的官方认证或背书。分享包不包含使用者的设备序列号、账号、传输文件、原始调试日志或本项目签名私钥。项目属于 [STEPX Advance](https://github.com/stepx-advance) 系列。
