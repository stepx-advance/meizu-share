# 构建快捷入口

构建工具提供 Linux、macOS 和 Windows 路径支持。需要适用本机系统和架构的 JDK 17、Android SDK platform 36 / build-tools 36.0.0，以及 Python 3.9+。安装和回滚不需要 JDK 或完整 SDK。

将独立签名密钥保存在项目目录以外。Linux 和 macOS 示例：

```sh
export SHARE_KIT_STORE_PASS='YOUR_LOCAL_STORE_PASSWORD'
python3 tools/build.py --sdk /path/to/android-sdk --java-home /path/to/jdk17 --keystore /path/to/private/share-kit.p12 --alias share-kit
```

Windows PowerShell 示例：

```powershell
$env:SHARE_KIT_STORE_PASS = 'YOUR_LOCAL_STORE_PASSWORD'
py -3 tools/build.py --sdk C:/path/to/android-sdk --java-home C:/path/to/jdk17 --keystore C:/path/to/private/share-kit.p12 --alias share-kit
```

口令经环境变量传给签名工具，不写入源码或产物。构建脚本不创建签名密钥。请保留并备份自己的密钥，不同签名不能直接覆盖同包名安装。

输出为 `dist/share-bridge.apk` 和 `dist/artifacts.json`。脚本只构建原创快捷入口，不修改或重新签名原厂 APK。构建完成后，重新计算分享包校验值。
