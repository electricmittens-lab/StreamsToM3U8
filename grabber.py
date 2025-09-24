#!/usr/bin/env python3
import re, requests
from bs4 import BeautifulSoup
from lxml import etree
from datetime import datetime, timedelta

# -------- Settings --------
OUTPUT_M3U = "exp.m3u"
OUTPUT_EPG = "exp.xml"
EXPTV_LOGO = "logo.png"
HTTP_TIMEOUT = 15

HEADERS = {
    "Referer": "https://exptv.org/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

OFFLINE_FALLBACK = "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4"

# -------- EXPTV video source --------
def grab_exptv():
    try:
        r = requests.get("https://exptv.org/", headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        tag = soup.find("source", {"id": "mp4_src"})
        if tag and tag.get("src"):
            return tag["src"].split("#")[0]
    except Exception as e:
        print(f"[EXPTV] error: {e}")
    return OFFLINE_FALLBACK

# -------- M3U Playlist --------
def update_m3u(exptv_url):
    epg_url = "https://raw.githubusercontent.com/electricmittens-lab/StreamsToM3U8/main/exp.xml"
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
        f.write(f'#EXTINF:-1 tvg-id="exptv" tvg-name="EXPTV" tvg-logo="{EXPTV_LOGO}", EXPTV\n')
        f.write(exptv_url + "\n")
    print(f"[EXPTV] Wrote {OUTPUT_M3U}")

# -------- EPG from daily JS --------
DAYS = ["sunday","monday","tuesday","wednesday","thursday","friday","saturday"]
BASE = "https://exptv.org/js/{}-3.js?v=001"

def fetch_day(day):
    try:
        url = BASE.format(day)
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[EXPTV] failed {day}: {e}")
        return ""

def parse_schedule(js_text):
    pattern = re.compile(
        r'\[\s*["\'](\d{1,2}:\d{2})["\']\s*,\s*["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']*)["\'])?(?:\s*,\s*["\']([^"\']*)["\'])?\s*\]'
    )
    return pattern.findall(js_text)

def build_epg():
    root = etree.Element("tv")
    chan = etree.SubElement(root, "channel", id="exptv")
    etree.SubElement(chan, "display-name").text = "EXPTV"

    today = datetime.utcnow()
    weekday = today.weekday()  # 0=Mon

    for offset, day in enumerate(DAYS):
        js_text = fetch_day(day)
        schedule = parse_schedule(js_text)
        if not schedule:
            continue

        base_date = today + timedelta(days=(offset-weekday))
        for i, (time_str, title, desc, poster) in enumerate(schedule):
            try:
                hour, minute = map(int, time_str.split(":"))
                start = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                if i + 1 < len(schedule):
                    nh, nm = map(int, schedule[i+1][0].split(":"))
                    stop = base_date.replace(hour=nh, minute=nm, second=0, microsecond=0)
                else:
                    stop = start + timedelta(hours=1)

                prog = etree.SubElement(
                    root, "programme", channel="exptv",
                    start=start.strftime("%Y%m%d%H%M%S +0000"),
                    stop=stop.strftime("%Y%m%d%H%M%S +0000")
                )
                etree.SubElement(prog, "title").text = title
                if desc:
                    etree.SubElement(prog, "desc").text = desc
                if poster:
                    etree.SubElement(prog, "icon", src=poster)
            except Exception as e:
                print(f"[EXPTV] bad entry {time_str}-{title}: {e}")

    with open(OUTPUT_EPG,"wb") as f:
        f.write(etree.tostring(root, pretty_print=True, encoding="utf-8"))
    print(f"[EXPTV] Wrote {OUTPUT_EPG}")

# -------- Main --------
if __name__ == "__main__":
    url = grab_exptv()
    update_m3u(url)
    build_epg()
