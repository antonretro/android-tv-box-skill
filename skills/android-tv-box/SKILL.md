---
name: android-tv-box
description: Turn a cheap Android TV box (MXQ Pro, X96, T95, H96 and other Amlogic/Rockchip/Allwinner boxes) into a clean, safe, great entertainment box over ADB - audit for backdoors, back up, malware-scan, lock open root, upgrade Kodi with a clean skin, load free TV + radio + weather channels, install YouTube (SmartTube), a modern launcher, retro games and speed tweaks. Use when the user plugs in an Android TV box and asks to set it up, clean it, check it, or "make it the best box ever".
---

# Android TV box makeover

A step-by-step routine to run with the user, one step at a time. Describe what will appear on the TV before each step. Keep replies short and plain, and say what's tested and what isn't.

## Ground rules

- **Back up before** removing or changing anything. Ask before flashing firmware.
- **Never type the user's passwords.** They sign in to apps on the TV themselves.
- **Legit sources only.** Don't install, test, fix or recommend unlicensed streaming apps or add-ons, and don't bypass DRM (Widevine) or device certification. If the box came "fully loaded" and the user chooses to keep those apps, leave them alone and don't lecture.
- **Check before pressing keys.** The user may be watching something. Take a screenshot first.
- Treat old boxes as entertainment-only: no personal logins (email, banking) on a box with years-old security patches.

## Tools

- `adb` (Android SDK Platform Tools). Find an existing copy before downloading: Android SDK `platform-tools`, or on PATH.
- `aapt` / `apksigner` from Android SDK build-tools, to check an APK before installing: `aapt dump badging app.apk` (look at `sdkVersion` and `native-code`), `apksigner verify --print-certs app.apk`.
- Python 3 for `build_channels.py` (in this folder).
- On Windows Git Bash, `export MSYS_NO_PATHCONV=1` so `/sdcard/...` paths aren't rewritten. Some sandboxes block adb's network socket (error 10013): run adb outside the sandbox.

## Driving the box

- Screenshot: `adb shell screencap -p /sdcard/sc.png` then `adb pull /sdcard/sc.png` (blank while video plays).
- Keys: `adb shell input keyevent 19/20/21/22` (arrows), `23` OK, `4` back, `3` home, `86` stop. `input tap X Y` (screen is usually 1280x720). Batch several keys in one `adb shell "..."` call; key presses are slow on these boxes.
- Current app: `adb shell dumpsys window windows | grep mCurrentFocus`.
- Copying from the box to the PC over Wi-Fi can be very slow. Run big pulls in the background.

## 1. Get in

1. On the box: Settings → Display → screen position/zoom 100%, output 1080p.
2. Settings → About → click **Build** (or Build number) 7 times → Developer options → **USB debugging** on.
3. About → Status → note the IP address.
4. `adb connect <ip>:5555`. The TV asks "Allow USB debugging?": tick **Always allow**, OK. Missed it? `adb disconnect` + `adb connect` shows it again.

## 2. Audit

Collect and report as tables:
- `getprop ro.product.model ro.board.platform ro.build.version.release ro.build.version.sdk ro.product.cpu.abilist ro.build.type ro.build.tags ro.build.version.security_patch`
- RAM (`/proc/meminfo`), storage (`df -h /data /system`), total flash (`/proc/partitions`)
- Root: `ls -l /system/xbin/su /system/bin/su`, `su -c id` as the shell user
- Apps: `pm list packages -3 -f`, and per app `dumpsys package <pkg>` for version, install date and risky permissions (RECEIVE_BOOT_COMPLETED, SYSTEM_ALERT_WINDOW, READ_PHONE_STATE, ACCESS_FINE_LOCATION, INSTALL_PACKAGES)
- Kodi: version, skin (`.kodi/userdata/guisettings.xml`, `lookandfeel.skin`), installed add-ons and repositories

Common findings on cheap boxes: a **32-bit-only system** even on a 64-bit chip (only armeabi-v7a apps install), `userdebug`/`test-keys` factory builds, security patches years old, **`su` that any app can run with no prompt**, an unknown preinstalled app store, and "fully loaded" Kodi builds with dozens of third-party repositories.

## 3. Back up and scan

- Pull every user-installed APK, `pm list packages -f`, `getprop`, the Kodi add-on list and the original `su` to a backup folder on the PC.
- Before any Kodi change: `tar -czf /sdcard/kodi-backup.tgz -C /sdcard/Android/data/org.xbmc.kodi/files .kodi`, pull it, verify it opens, delete the copy on the box.
- Scan the pulled APKs with the PC's antivirus (e.g. Windows Defender `MpCmdRun.exe -Scan -ScanType 3 -File <folder> -DisableRemediation`). Say plainly that desktop scanners only partly cover Android apps.
- **Adware / malware check:** pull *every* user app plus the box maker's extra system apps (store, cleaner, browser, launcher), then run `python scan_apks.py <folder>` (in this folder). It looks inside each APK for ad SDKs (AdMob, AppLovin, StartApp, Airpush…), trackers, risky permissions (boot start, drawing over apps, silent installs, phone ID, location) and red flags (packed code, hidden APKs in assets). Report a table: app, verdict (ADWARE / ADS / CHECK / ok), why. Offer to remove ADWARE and ADS apps; for system apps, disable instead (`pm disable-user --user 0 <pkg>`). Re-run after removals, and check again at the end of the makeover.
- Also watch for: apps that show pop-ups or full-screen ads, "cleaner"/"booster" apps, unknown app stores, and apps that start at boot and draw over the screen.

## 4. Clean and secure

- Uninstall only what the user agrees to (dead apps, flagged apps): `adb uninstall <pkg>`. Make sure each APK is in the backup first.
- Typical junk on "fully loaded" boxes: an unknown preinstalled app store, a "cleaner"/"booster"/"start manager" app, a root file manager with ads, Kodi add-on installers that ask for contacts or location, and outdated streaming apps with several ad networks. Box-maker system apps (media casting, file browser, video player) are usually fine to keep.
- **Switch off the OTA updater by default** (on Amlogic boxes often "UPDATE&BACKUP", `com.droidlogic.otaupgrade`): `pm disable-user --user 0 <pkg>`. Its "local update" rewrites the whole system, and a firmware file for the wrong clone board bricks the box; cheap boxes rarely get real updates anyway. Tell the user, and re-enable it (`pm enable <pkg>`) only to install an official firmware file. Recovery-mode flashing still exists but needs a button held at power-on, so it won't happen by accident.
- If the user keeps an app that has ads or risky permissions, revoke what Android allows: `pm revoke <pkg> android.permission.RECORD_AUDIO` (runtime permissions only). Don't patch ads out of other people's apps.
- To hide apps just for a screenshot without deleting anything: `pm disable-user --user 0 <pkg>`, capture, then `pm enable <pkg>` in the same command.
- After removals, run `scan_apks.py` again and show the new results.
- If `su` is open to everyone, lock it to root:
  `su -c 'mount -o rw,remount /system && chmod 0700 /system/xbin/su && chown root:root /system/xbin/su && mount -o ro,remount /system'`
  then confirm `su -c id` as the shell user gives "Permission denied". On debug builds `adb root` still works for maintenance.

## 5. Kodi

- Install the **latest official Kodi** from `https://mirrors.kodi.tv/releases/android/` (`arm/` = 32-bit, `arm64/` = 64-bit). It's signed by the XBMC Foundation; if the box's Kodi has the same signer it upgrades in place. Warn first: Kodi 19+ drops old Python 2 add-ons.
- If an upgrade sits on "Add-on migration in progress" for a long time (dead third-party repositories timing out): force-stop Kodi, back up `userdata/Database/AddonsNN.db` (highest NN), set `enabled=0` in table `installed` for every `repository.%` except `repository.xbmc.org`, restart.
- Clean look: force-stop Kodi, set `lookandfeel.skin` to `skin.estuary` in `guisettings.xml` (back it up). Some builds pop a wizard asking to switch back: answer No.
- Live TV add-on: Kodi's official repository → PVR clients → **PVR IPTV Simple Client**. Settings file: `addon_data/pvr.iptvsimple/instance-settings-1.xml` (Kodi 20+) or `settings.xml` (Kodi 18).

## 6. Free TV, radio and weather

1. Ask which countries the user wants. Big lists (10,000+ channels) lag on 1 GB boxes; a few countries (about 2,000-2,500 entries) stay smooth.
2. `python build_channels.py iptv-box.m3u CA,US,GB` builds one playlist with:
   - TV channels from [iptv-org](https://github.com/iptv-org/iptv) for those countries, minus `[Geo-blocked]` and `[Not 24/7]`
   - a **Weather** group (iptv-org Weather category)
   - popular stations per country from [Radio Browser](https://www.radio-browser.info), marked `radio="true"` so they appear in Kodi's **Radio** section
3. Push it to `/sdcard/Android/data/org.xbmc.kodi/files/.kodi/userdata/iptv/channels.m3u`, set `m3uPathType` 0 and `m3uPath` to that file, delete `iptv.m3u.cache`, restart Kodi and look for `Loaded N channels` in `.kodi/temp/kodi.log`.
4. On the TV: TV → Channels → press Left → Group → pick a country.
- Some iptv-org entries are unofficial rebroadcasts (raw `IP:port` relays). Don't pick or test those for the user.
- If a dead stream freezes Kodi: `input keyevent 86` (stop), then `am force-stop org.xbmc.kodi`.

## 7. Apps

Install with `adb install -r app.apk` after checking `sdkVersion` (must be ≤ the box's SDK) and `native-code` (must include the box's ABI; on 32-bit systems add `--abi armeabi-v7a`).

| App | Official source | Notes |
|---|---|---|
| SmartTube (YouTube) | github.com/yuliskov/SmartTube/releases | Google's YouTube TV app doesn't run on plain Android boxes |
| Projectivy Launcher | github.com/spocky/miproja1/releases | Keep the original launcher installed; the user picks the default home app |
| RetroArch | buildbot.libretro.com | 32-bit "ra32" build for 32-bit systems; uses the user's own game files |
| Pluto TV, Tubi, Plex | Their store listings | Free, legit, ad-supported. Newest versions may need a newer Android; check minSdk |
| The user's own APKs | wherever they keep them | Check the ABI; a 64-bit-only build won't install on a 32-bit system (rebuild with ARMv7 enabled) |

App stores that fetch from Google Play anonymously (e.g. Aurora) often can't see TV-only apps on uncertified boxes; direct APKs from the developer are more reliable.

## 8. Speed

- `settings put global window_animation_scale 0.5` (and `transition_animation_scale`, `animator_duration_scale`).
- Stop junk from auto-starting by disabling it, with the user's OK (`pm disable-user --user 0 <pkg>`), rather than uninstalling.
- Fewer Kodi add-ons and repositories = faster Kodi start.
- Ethernet beats Wi-Fi for live streams.
- Avoid "RAM booster" / "cleaner" apps.

## 9. Bigger upgrades (ask first)

- **CoreELEC** from a microSD card: newest Kodi, very fast, Android untouched (check chip support).
- **Community Android TV ROMs**: risk of bricking. Have a USB-A to USB-A cable and the chip vendor's flashing tool ready, and try on a spare box first.
- Netflix/Disney+/Prime on uncertified boxes usually only get Widevine L3 (SD). Google's official uncertified-device registration fixes Play services, not HD.

## 10. Finish

Write a short `AGENTS.md`/notes file for the box (IP, specs, what was done, where the backups are, what's left), so the next session or another assistant can pick up.
