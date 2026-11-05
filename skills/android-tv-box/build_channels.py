"""Build one Kodi IPTV Simple playlist: TV channels for chosen countries,
a Weather group, and popular radio stations (Kodi's Radio section).

Sources (free, public, no account):
  iptv-org   https://iptv-org.github.io/iptv/index.country.m3u   (TV, by country)
             https://iptv-org.github.io/iptv/index.category.m3u  (Weather category)
  Radio Browser https://de1.api.radio-browser.info               (radio)

Drops [Geo-blocked] and [Not 24/7] channels. Big lists (10k+) lag on 1 GB
boxes; keep it to a few countries (about 2-2.5k entries is smooth).

Run:  python -I build_channels.py <out.m3u> [CC,CC,...]
      default countries: CA,US,GB
"""
import json
import re
import sys
import urllib.request

UA = {"User-Agent": "android-tv-box-setup/1.0"}
NAMES = {"CA": "Canada", "US": "United States", "GB": "United Kingdom", "IT": "Italy",
         "MT": "Malta", "AU": "Australia", "IE": "Ireland", "NZ": "New Zealand",
         "FR": "France", "DE": "Germany", "ES": "Spain", "MX": "Mexico"}
RADIO_PER_COUNTRY = 60


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read().decode("utf-8")


def blocks(m3u):
    lines = m3u.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("#EXTINF"):
                j += 1
            yield [x for x in lines[i:j] if x.strip()]
            i = j
        else:
            i += 1


def ok(head):
    return "[Geo-blocked]" not in head and "[Not 24/7]" not in head


def main():
    out = sys.argv[1]
    codes = (sys.argv[2] if len(sys.argv) > 2 else "CA,US,GB").upper().split(",")
    want = {NAMES.get(c, c) for c in codes}

    res = ["#EXTM3U"]
    counts = {}
    for b in blocks(get("https://iptv-org.github.io/iptv/index.country.m3u")):
        g = re.search(r'group-title="([^"]*)"', b[0])
        if g and g.group(1) in want and ok(b[0]):
            res += b
            counts[g.group(1)] = counts.get(g.group(1), 0) + 1

    w = 0
    for b in blocks(get("https://iptv-org.github.io/iptv/index.category.m3u")):
        if 'group-title="Weather"' in b[0] and ok(b[0]):
            res += b
            w += 1

    r = 0
    for cc in codes:
        nm = NAMES.get(cc, cc)
        st = json.loads(get("https://de1.api.radio-browser.info/json/stations/search?countrycode="
                            f"{cc}&hidebroken=true&order=clickcount&reverse=true&limit={RADIO_PER_COUNTRY * 2}"))
        seen, n = set(), 0
        for s in st:
            url = s.get("url_resolved") or s.get("url")
            name = (s.get("name") or "").strip().replace(",", " ")
            if not url or not name or name.lower() in seen:
                continue
            if (s.get("codec") or "").upper() not in ("MP3", "AAC", "AAC+", "OGG", ""):
                continue
            seen.add(name.lower())
            logo = (s.get("favicon") or "").replace('"', "")
            res += [f'#EXTINF:-1 radio="true" tvg-logo="{logo}" group-title="Radio - {nm}",{name}', url]
            n += 1
            if n >= RADIO_PER_COUNTRY:
                break
        r += n

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(res) + "\n")
    print("TV:", counts, "| weather:", w, "| radio:", r, "| total:", sum(counts.values()) + w + r)


if __name__ == "__main__":
    main()
