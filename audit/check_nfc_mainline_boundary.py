#!/usr/bin/env python3
"""Android17 PE-Reborn row 166: pinned NXP legacy/Mainline NFC source boundary.

Checks source/module identity and active manifest only. NO Soong build or runtime.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OLD_SHA = "77d16cbcd5905c66305b05a67d21aedbc21ce5af"
OLD_TREE = "880cffd655da21807c27730c490a8a84e09610bb"
AOSP_SHA = "940212c440f57032a19cf0f90c7faa8eca48d546"
AOSP_TREE = "da01c841e3238648d0ae33c3392c05f1552e63d5"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def git(path, *args):
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True).strip()


def content(path, sha, file):
    return git(path, "show", f"{sha}:{file}")


def pin(path, ref, sha, tree, label):
    actual = git(path, "rev-parse", f"{ref}^{{commit}}")
    require(actual == sha, f"{label} commit mismatch: {actual}")
    tree_actual = git(path, "rev-parse", f"{actual}^{{tree}}")
    require(tree_actual == tree, f"{label} Git tree mismatch: {tree_actual}")
    return actual


def old_nxp(path):
    sha = pin(path, "refs/remotes/origin/seventeen",
              OLD_SHA, OLD_TREE, "PE legacy NFC")
    main = content(path, sha, "SN100x/src/Android.bp")
    utils = content(path, sha, "SN100x/utils/Android.bp")
    adap = content(path, sha, "SN100x/src/adaptation/NfcAdaptation.cc")
    conf = content(path, sha, "conf/libnfc-nci.conf")
    root_bp = content(path, sha, "Android.bp")
    require('name: "libsn100nfc-nci"' in main and
            "system_ext_specific: true" in main,
            "legacy SN100 NFC library source changed")
    for dep in ("android.hardware.nfc@1.0", "android.hardware.nfc@1.1",
                "android.hardware.nfc@1.2", "vendor.nxp.hardware.nfc@2.0",
                "libchrome", "libstatslog"):
        require(f'"{dep}"' in main, f"legacy NFC dependency changed: {dep}")
    require('name: "libsn100nfcutils"' in utils
            and '"libc++fs"' in utils,
            "legacy NFC utils/test C++ dependency changed")
    require("#include <android/hardware/nfc/1.2/INfc.h>" in adap
            and "<vendor/nxp/hardware/nfc/2.0/INqNfc.h>" in adap,
            "legacy NXP HIDL client contract changed")
    require('NFA_STORAGE="/data/nfc"' in conf
            and "SCREEN_OFF_POWER_STATE=1" in conf
            and "NFA_MAX_EE_SUPPORTED=0x02" in conf,
            "legacy NFC configuration changed")
    require('subdirs = ["src", "utils"]' in root_bp,
            "legacy Soong root changed")
    print("PASS: pinned 2022 NXP SN100x HIDL source + old utils/config")


def official_nfc(path):
    sha = pin(path, "FETCH_HEAD", AOSP_SHA, AOSP_TREE,
              "official AOSP17 NFC Mainline")
    bp = content(path, sha, "libnfc-nci/src/Android.bp")
    util = content(path, sha, "libnfc-nci/utils/Android.bp")
    apex = content(path, sha, "apex/Android.bp")
    for token in ('name: "libnfc-nci"', '"android.hardware.nfc-V2-ndk"',
                  '"libnfc-nci_flags"', '"com.android.nfcservices"',
                  'min_sdk_version: "36"'):
        require(token in bp, "official Mainline NFC stack changed: " + token)
    require('name: "libnfcutils"' in util
            and '"com.android.nfcservices"' in util,
            "official AOSP17 NFC util/APEX changed")
    require('name: "com.android.nfcservices"' in apex
            and 'apps: ["NfcNciApex"]' in apex,
            "official NFC Mainline APEX changed")
    require("nfc_nci_fuzzer" in bp and
            "nfc_rw_fuzzer" in bp and "nfc_ce_fuzzer" in bp,
            "official AOSP17 NFC fuzz targets changed")
    print("PASS: official AOSP17 Mainline NFC has AIDL V2, APEX and fuzzers")


def active_manifest(path):
    path = Path(path)
    entry = ET.parse(path / "default.xml").getroot()
    require(len(entry) == 1 and
            entry[0].get("name") == "aosp17_pe_p2_kernel_configs.xml",
            "PE-Reborn active source-only manifest entrypoint changed")
    root = ET.parse(path / "aosp17_pe_bootstrap.xml").getroot()
    owners = {p.get("path"): p.get("name") for p in root.findall("project")}
    require(owners.get("packages/modules/Nfc") == "platform/packages/modules/Nfc",
            "official Mainline NFC owner has been replaced")
    require(owners.get("hardware/nxp/nfc") == "platform/hardware/nxp/nfc",
            "official NFC HAL owner has been replaced")
    require("vendor/nxp/opensource/commonsys/external/libnfc-nci" not in owners
            and "vendor_nxp_opensource_commonsys_external_libnfc-nci"
            not in owners.values(),
            "legacy NXP NFC stack unexpectedly active")
    subprocess.run(
        [sys.executable, str(path / "tools/validate_aosp17_base_profiles.py")],
        check=True, cwd=path)
    print("PASS: current staged PE-Reborn AOSP17 keeps official Mainline NFC source")


def main():
    require(len(sys.argv) == 4,
            "usage: check_nfc_mainline_boundary.py LEGACY_PE OFFICIAL_NFC AOSP17_MANIFEST")
    old, aosp, manifest = [Path(p).resolve() for p in sys.argv[1:]]
    require(all(p.is_dir() for p in (old, aosp, manifest)),
            "missing a required checked-out tree")
    old_nxp(old)
    official_nfc(aosp)
    active_manifest(manifest)
    print("PASS: row 166 NFC Mainline ownership/source-only audit")
    print("OPEN: modern NXP release diff, AIDL HAL/SE, Soong/APEX, VINTF,")
    print("      SELinux enforcing, device compilation and physical NFC tests")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, ET.ParseError,
            subprocess.CalledProcessError) as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
