# SPDX-License-Identifier: MIT
"""Build only the project's original Android entry application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    subprocess.run([str(x) for x in args], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sdk", type=Path, required=True)
    p.add_argument("--java-home", type=Path, required=True)
    p.add_argument("--build-tools", default="36.0.0")
    p.add_argument("--keystore", type=Path, required=True)
    p.add_argument("--alias", default="share-kit")
    args = p.parse_args()
    if not os.environ.get("SHARE_KIT_STORE_PASS"):
        raise RuntimeError("Set SHARE_KIT_STORE_PASS; signing credentials are not stored by this script.")
    os.environ["JAVA_HOME"] = str(args.java_home)
    suffix = ".exe" if os.name == "nt" else ""
    batch = ".bat" if os.name == "nt" else ""
    tools = args.sdk / "build-tools" / args.build_tools
    sdk_jar = args.sdk / "platforms" / "android-36" / "android.jar"
    out = ROOT / "build"
    if out.exists():
        shutil.rmtree(out)
    classes, dex = out / "classes", out / "dex"
    classes.mkdir(parents=True, exist_ok=True)
    dex.mkdir(exist_ok=True)
    run([tools / ("aapt2" + suffix), "compile", "--dir", ROOT / "app/res", "-o", out / "resources.zip"])
    run([tools / ("aapt2" + suffix), "link", "-I", sdk_jar, "--manifest", ROOT / "app/AndroidManifest.xml", "-o", out / "unsigned.apk", out / "resources.zip"])
    run([args.java_home / "bin" / ("javac" + suffix), "-encoding", "UTF-8", "-source", "8", "-target", "8", "-bootclasspath", sdk_jar, "-d", classes, *sorted((ROOT / "app/src").rglob("*.java"))])
    run([tools / ("d8" + batch), "--min-api", "34", "--lib", sdk_jar, "--output", dex, *sorted(classes.rglob("*.class"))])
    with zipfile.ZipFile(out / "unsigned.apk", "a") as z:
        z.write(dex / "classes.dex", "classes.dex", compress_type=zipfile.ZIP_DEFLATED)
    run([tools / ("zipalign" + suffix), "-P", "16", "-f", "4", out / "unsigned.apk", out / "aligned.apk"])
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    apk = dist / "share-bridge.apk"
    run([tools / ("apksigner" + batch), "sign", "--ks", args.keystore, "--ks-key-alias", args.alias, "--ks-pass", "env:SHARE_KIT_STORE_PASS", "--key-pass", "env:SHARE_KIT_STORE_PASS", "--out", apk, out / "aligned.apk"])
    verification = subprocess.run([str(tools / ("apksigner" + batch)), "verify", "--print-certs", str(apk)],
                                  check=True, capture_output=True, text=True)
    certificate = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]{64})", verification.stdout)
    if certificate is None:
        raise RuntimeError("Could not read signing certificate fingerprint.")
    record = {"package": "local.pz261a.shareentry", "version": "1.0",
              "bridge_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
              "signer_certificate_sha256": certificate.group(1).lower()}
    engine = ROOT / "third_party/meizu/mzshare-6.1.14.apk"
    if engine.exists():
        record["engine"] = {"file": "third_party/meizu/mzshare-6.1.14.apk", "package": "com.meizu.share",
                            "version": "6.1.14", "version_code": 6001014,
                            "sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
                            "signer_certificate_sha256": "94153299d67ab1b37a39ed5fe17e893df87084fb129077be51863bcbd9132336"}
    (dist / "artifacts.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("Built original bridge APK; no third-party engine is included.")


if __name__ == "__main__":
    main()
