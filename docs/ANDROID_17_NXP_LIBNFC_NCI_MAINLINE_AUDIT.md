# PE-Reborn Android 17 — row 166: NXP legacy libnfc-nci vs Mainline NFC

**Audit date:** 2026-11-07. **Target platform:** independent AOSP17-based PixelExperience-Reborn.
**Future device:** POCO F5 Pro / Redmi K60 (`mondrian`, Qualcomm SM8475) only.
**Status:** source/dependency/architecture audit. NO Soong build, test image, or physical device evaluation.

## Decision

**Keep the official Android 17 NFC Mainline stack as the baseline. Do not add `vendor/nxp/opensource/commonsys/external/libnfc-nci` to the active manifest.** The 2022 archived NXP source is a separate NFC controller-to-framework implementation linked against older NXP vendor HIDL APIs. It does not represent a compatible modern Android17 replacement for the NFC Mainline package merely because the repo path contains `libnfc-nci`. The namespace/module names are not all exact duplicates, but enabling parallel stacks risks conflicting HAL binding, APEX ownership, configuration, extra vendor dependencies and ambiguous runtime behaviour.

**Do not use LF52406's LineageOS-derived mondrian/sm8450-common trees as the foundation of the PE-Reborn platform.** They may be consulted later for *specific* hardware facts or a uniquely useful well-reviewed solution, then independently re-evaluated against current AOSP17, firmware and security requirements. No device tree, configuration, proprietary library or kernel patch is imported by this audit.

## Pinned source inventory

| Source | Immutable identity | Reviewed evidence |
| --- | --- | --- |
| Historical PE-Reborn `vendor_nxp_opensource_commonsys_external_libnfc-nci` `seventeen` | commit `77d16cbcd5905c66305b05a67d21aedbc21ce5af`, tree `880cffd655da21807c27730c490a8a84e09610bb`, committed 2022-09-05 | `SN100x/src/Android.bp` defines `libsn100nfc-nci` (`system_ext_specific`), depends on NFC HIDL `android.hardware.nfc@1.0/1.1/1.2`, legacy `vendor.nxp.hardware.nfc@1.0/1.1/2.0`, `libhidlbase`, `libchrome` and `libstatslog`; `SN100x/src/adaptation/NfcAdaptation.cc` binds old HIDL `INfc`, `INqNfc`. |
| Legacy utility/test modules (same PE revision) | same commit | `SN100x/utils/Android.bp` exports `libsn100nfcutils`; its `sn100nfc_test_utils` still requests `libc++fs`, which is not an approved Android17 standalone build dependency. `conf/Android.bp` installs `libnqnfc-nci.conf-default` with legacy config. |
| Official Android17 NFC Mainline `packages/modules/Nfc` | tag `android-17.0.0_r1`, commit `940212c440f57032a19cf0f90c7faa8eca48d546`, tree `da01c841e3238648d0ae33c3392c05f1552e63d5` | `libnfc-nci/src/Android.bp` owns modern module `libnfc-nci`, includes `android.hardware.nfc-V2-ndk` (AIDL V2) while also retaining some HIDL compatibility objects, `libnfc-nci_flags`, stats support, fuzzers, strict `visibility` and `com.android.nfcservices` APEX availability. |
| Official AOSP17 `libnfc-nci/utils/Android.bp` | same tag | `libnfcutils` has host support, bounded visibility and APEX availability; AOSP17 uses its own utility/config handling. |
| Official Android17 NFC APEX | same tag | `apex/Android.bp` owns `com.android.nfcservices` and `NfcNciApex`, and optionally installs a default `libnfc-nci.conf`. Keep one coherent app/native/APEX owner; do not blindly overlay the archived NXP config. |

Primary official sources:
- https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-17.0.0_r1/libnfc-nci/src/Android.bp
- https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-17.0.0_r1/libnfc-nci/utils/Android.bp
- https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-17.0.0_r1/apex/Android.bp
- https://github.com/PixelExperience-Reborn/vendor_nxp_opensource_commonsys_external_libnfc-nci/tree/seventeen

### Modern NXP candidate (separate from old PE)

The NXP vendor document repository identifies an Android17 `17.07.00` source release, targeting PN557/PN560/SN100/SN110/SN220/SN300. **Candidate for comparison, NOT integrated or verified with the independent device build.** A vendor release and list of supported controller families do not establish the exact NFC IC, firmware, eSE routing or interoperability of any particular mondrian revision, nor automatically supersede AOSP17 source for PE-Reborn.

Reference: https://github.com/NXPNFCProject/NFC_NCIHAL_docs (17.07.00 listing). Compare immutable upstream tag and exact licence/security patches before making an actual code-change proposal.

## Modernisation decisions, technology candidates and constraints

| Candidate | Decision | Why / acceptance |
| --- | --- | --- |
| Official NFC Mainline `packages/modules/Nfc` (AOSP17) | **RETAIN** | One source owner, NFC app/APEX native stack, modern build integration and upstream security/feature evolution. Verify actual independent build. |
| NFC AIDL V2 through `android.hardware.nfc-V2-ndk` | **RETAIN BASELINE; VERIFY HAL** | Present in AOSP17 `libnfc-nci` as well as legacy HIDL compatibility. Do not assume the actual vendor service or device uses AIDL V2 until VINTF/service tests. |
| `com.android.nfcservices` APEX and restricted `libnfc-nci` API | **RETAIN BASELINE** | APEX ownership, visibility, min-SDK and signing are security/build boundaries. Do not ship the old `system_ext` NFC implementation as a parallel replacement. |
| AOSP17 NFC fuzzing/overflow checks/flags | **RETAIN BASELINE** | Existing upstream security engineering. Any NXP backport must preserve bounds/overflow hardening, avoid forcing permissive policy and pass fuzz/host gates. |
| NXP 17.07.00 Android17 source | **REVIEW LATER (OPTIONAL)** | Evaluate only an exact upstream release diff for a known required hardware problem, preserving provenance, licensing and immutable source SHA; validate in AOSP17 build and on real hardware before adopting. |
| Archived `libsn100nfc-nci` (2022) / old HIDL vendor extensions | **DO NOT ACTIVATE** | HIDL-only NXP stack, old `libchrome`/`libstatslog` dependencies, old `libc++fs` test, no demonstrated Android17 APEX integration or current device requirement. |
| Device-specific NFC/eSE configuration, potentially from another ROM | **CONDITIONAL EXCEPTION** | Only after independent AOSP17 baseline review and supported physical NFC controller/VINTF/firmware proof, with minimal isolated changes and tests; never wholesale import. |

### Risks specific to the historical NXP repository

1. `libsn100nfc-nci` is a separate `system_ext_specific` NFC stack; it does **not** automatically replace the AOSP `libnfc-nci` module or Mainline. Enabling both without a consumer map is unjustified.
2. The old `NfcAdaptation.cc` binds to HIDL 1.x and `vendor.nxp.hardware.nfc` 2.0. Modern AOSP17 supports NFC AIDL V2 and carries its own compatibility layer. Do not graft legacy Binder lifetime, callbacks or vendor extension into the APEX.
3. `libc++fs` used by an archived host/device test is not provided by the reviewed AOSP17 external/libcxx source graph. Do not resurrect it globally; update a legitimate test consumer only after a reviewed modern port exists.
4. The old configuration uses `NFA_STORAGE="/data/nfc"`, `SCREEN_OFF_POWER_STATE=1`, `NFA_MAX_EE_SUPPORTED=0x02` and AID routing defaults. These are not safe defaults for an unverified modern product/SE and must not be installed speculatively.
5. Source ownership is not runtime ownership. NFC HAL vs NFC JNI/framework vs eSE/OMAPI vs vendor firmware are distinct subsystems. Do not confuse Android17 `packages/modules/Nfc` with `hardware/nxp/nfc`.

## Future approval gates (when device bring-up is actually started)

1. **Exact upstream inventory:** immutable AOSP17 `packages/modules/Nfc` source/trees and any proposed NXP 17.07.00 diff; explicit source licences, export restrictions and maintainability.
2. **Consumer graph:** map AIDL NFC HAL service, `android.hardware.nfc.INfc/default`, Secure Element/OMAPI, NFC JNI stack, `NfcNciApex`, device overlays and vendor libraries without duplicates.
3. **Independent PE device/product:** no direct dependency on LineageOS product, `lineage-sdk`, `vendor/lineage` or its device makefiles. The original LF52406 tree can be consulted for a specific device signal and separately checked.
4. **Security gates:** Soong build, stable AIDL interface compatibility, VINTF+FCM, NFC APEX signing/update model, SELinux enforcing/neverallow and memory-safety/fuzz tests.
5. **Device behavior:** reader/writer tags, HCE and wallet if licensed/supported, eSE/UICC routing, reboot/suspend, low-power/screen-off, airplane mode, multi-user, NFC recovery, OEM firmware version and regression logs.
6. **Performance/power:** compare measured energy, latency and stability under normal and repeated NFC discovery. Do not promise improvement based only on the version number of NXP source.

## Changes in this audit

- Independent audit branch, source-only pinned checker and GitHub Actions CI.
- Reviewed manifest working branch guards against legacy `vendor/nxp/opensource/commonsys/external/libnfc-nci` checkout and repo name and retains the official NFC Mainline owner.
- Negative tests intentionally activate/replace the old source; the validator must reject the mutation.
- No active NFC source override, new vendor Soong import, data/SE setting, Android17 device tree, package, proprietary firmware, or kernel change.

**NOT DONE:** complete Soong/APEX build, vendor ABI tests, VINTF/SELinux, CTS/VTS, device NFC functionality or physical mondrian testing. Passing host/source validation is NOT proof of these capabilities.
