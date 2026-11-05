"""Scan Android APKs for ad libraries, risky permissions and other red flags.

Static check only: it looks inside each APK (class names in the dex files,
the manifest, bundled files). It does not run anything. A hit is a reason to
look closer, not proof of malware, and a clean result is not a guarantee.
Pair it with a real antivirus scan.

Run:  python -I scan_apks.py <folder with .apk files> [--aapt path\to\aapt.exe]
"""
import argparse
import os
import re
import subprocess
import sys
import zipfile

# Class/package prefixes of advertising and push-ad SDKs (as they appear in dex: "Lcom/foo/").
AD_SDKS = {
    "Google AdMob": "Lcom/google/android/gms/ads/",
    "Google Mobile Ads (old)": "Lcom/google/ads/",
    "Facebook Audience Network": "Lcom/facebook/ads/",
    "AppLovin": "Lcom/applovin/",
    "Unity Ads": "Lcom/unity3d/ads/",
    "ironSource": "Lcom/ironsource/",
    "MoPub": "Lcom/mopub/",
    "StartApp": "Lcom/startapp/",
    "InMobi": "Lcom/inmobi/",
    "Vungle": "Lcom/vungle/",
    "Chartboost": "Lcom/chartboost/",
    "AdColony": "Lcom/adcolony/",
    "Tapjoy": "Lcom/tapjoy/",
    "Yandex Ads": "Lcom/yandex/mobile/ads/",
    "Mintegral": "Lcom/mbridge/",
    "Pangle (ByteDance)": "Lcom/bytedance/sdk/openadsdk/",
    "Amazon Ads": "Lcom/amazon/device/ads/",
    "Smaato": "Lcom/smaato/",
    "Appodeal": "Lcom/appodeal/",
    "AdBuddiz": "Lcom/purplebrain/adbuddiz/",
    # aggressive / adware-style SDKs
    "Airpush (adware)": "Lcom/airpush/",
    "Leadbolt (adware)": "Lcom/pad/android/",
    "Mobvista": "Lcom/mobvista/",
    "Batmobi": "Lcom/batmobi/",
    "Kuguo (adware)": "Lcom/kuguo/",
    "Adwo (adware)": "Lcom/adwo/",
    "Waps (adware)": "Lcom/waps/",
    "Youmi (adware)": "Lnet/youmi/",
    "Domob (adware)": "Lcn/domob/",
}
TRACKERS = {
    "Facebook SDK": "Lcom/facebook/appevents/",
    "Flurry": "Lcom/flurry/",
    "AppsFlyer": "Lcom/appsflyer/",
    "Adjust": "Lcom/adjust/sdk/",
    "Umeng": "Lcom/umeng/",
}
RISKY_PERMS = {
    "android.permission.RECEIVE_BOOT_COMPLETED": "starts itself at boot",
    "android.permission.SYSTEM_ALERT_WINDOW": "can draw over other apps (pop-ups)",
    "android.permission.INSTALL_PACKAGES": "can install apps silently (system only)",
    "android.permission.REQUEST_INSTALL_PACKAGES": "can ask to install other apps",
    "android.permission.READ_PHONE_STATE": "reads device ID / phone state",
    "android.permission.ACCESS_FINE_LOCATION": "precise location",
    "android.permission.ACCESS_COARSE_LOCATION": "rough location",
    "android.permission.GET_ACCOUNTS": "lists accounts on the device",
    "android.permission.READ_CONTACTS": "reads contacts",
    "android.permission.RECORD_AUDIO": "microphone",
    "android.permission.CHANGE_WIFI_STATE": "changes Wi-Fi settings",
    "android.permission.WRITE_SETTINGS": "changes system settings",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "accessibility service (can read the screen)",
    "android.permission.BIND_DEVICE_ADMIN": "device admin (hard to uninstall)",
}
PACKERS = {  # code packers/protectors often used to hide what an app does
    "libjiagu": "Qihoo 360 Jiagu packer",
    "libsecexe": "Bangcle packer",
    "libDexHelper": "Bangcle/SecNeo packer",
    "libshell": "generic shell packer",
    "libprotectClass": "packer",
    "libtup": "Tencent packer",
    "libnqshield": "NQ shield packer",
}


def dex_hits(z):
    found_ads, found_trk = set(), set()
    for name in z.namelist():
        if re.fullmatch(r"(classes\d*\.dex)|(.+\.dex)", name.split("/")[-1]):
            data = z.read(name)
            for label, pref in AD_SDKS.items():
                if pref.encode() in data:
                    found_ads.add(label)
            for label, pref in TRACKERS.items():
                if pref.encode() in data:
                    found_trk.add(label)
    return found_ads, found_trk


def other_flags(z):
    flags = []
    names = z.namelist()
    for n in names:
        base = n.split("/")[-1].lower()
        for k, v in PACKERS.items():
            if base.startswith(k.lower()):
                flags.append(f"packed code: {v} ({n})")
        if base.endswith((".apk", ".jar", ".dex")) and n.startswith("assets/"):
            flags.append(f"hidden app/code inside assets: {n}")
    return sorted(set(flags))


def manifest(aapt, apk):
    if not aapt:
        return "", "", []
    try:
        out = subprocess.run([aapt, "dump", "badging", apk], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60).stdout or ""
    except Exception:
        return "", "", []
    pkg = (re.search(r"package: name='([^']+)'", out) or [None, ""])[1]
    label = (re.search(r"application-label:'([^']*)'", out) or [None, ""])[1]
    perms = re.findall(r"uses-permission: name='([^']+)'", out)
    return pkg, label, perms


def find_aapt():
    sdk = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "build-tools")
    if os.path.isdir(sdk):
        for v in sorted(os.listdir(sdk), reverse=True):
            p = os.path.join(sdk, v, "aapt.exe" if os.name == "nt" else "aapt")
            if os.path.exists(p):
                return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--aapt", default=None)
    a = ap.parse_args()
    aapt = a.aapt or find_aapt()
    apks = sorted(f for f in os.listdir(a.folder) if f.lower().endswith(".apk"))
    if not apks:
        sys.exit("no .apk files found")
    print(f"Scanned {len(apks)} apps (static check; not a guarantee)\n")
    worst = []
    for f in apks:
        path = os.path.join(a.folder, f)
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            print(f"!! {f}: not a valid APK")
            continue
        ads, trk = dex_hits(z)
        flags = other_flags(z)
        pkg, label, perms = manifest(aapt, path)
        risky = [f"{p.split('.')[-1]} ({RISKY_PERMS[p]})" for p in perms if p in RISKY_PERMS]
        verdict = "ADS" if ads else ("CHECK" if flags or len(risky) >= 3 else "ok")
        if any("adware" in x for x in ads):
            verdict = "ADWARE"
        worst.append((verdict, label or f))
        print(f"[{verdict}] {label or '?'}  ({pkg or f})")
        if ads:
            print("   ad libraries: " + ", ".join(sorted(ads)))
        if trk:
            print("   trackers: " + ", ".join(sorted(trk)))
        if risky:
            print("   permissions: " + "; ".join(risky))
        for fl in flags:
            print("   " + fl)
    print("\nSummary:")
    for tag in ("ADWARE", "ADS", "CHECK"):
        items = [n for v, n in worst if v == tag]
        if items:
            print(f"  {tag}: " + ", ".join(items))
    print("  Remember: system apps from the box maker can look 'risky' (boot, overlays) and be normal.")


if __name__ == "__main__":
    main()
