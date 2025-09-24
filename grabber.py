#!/usr/bin/env python3
import requests
import re
from lxml import etree
from datetime import datetime, timedelta
import pytz

# -------- Settings --------
OUTPUT_M3U = "exp.m3u"
OUTPUT_XML = "exp.xml"
OFFLINE_FALLBACK = "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4"
EXPTV_LOGO = "logo.png"
TIMEZONE = pytz.timezone("America/Chicago")
# --------------------------

# -------- Grab EXPTV stream --------
def grab_exptv():
    try:
        r = requests.get("https://exptv.org/js/main.js", timeout=10)
        r.raise_for_status()
        match = re.search(r'content2/([A-Za-z0-9_-]+\.mp4)', r.text)
        if match:
            url = f"https://exptv.org/content2/{match.group(1)}"
            print(f"✅ Found EXPTV stream: {url}")
            return url
        print("⚠️ No MP4 found in main.js, using fallback.")
        return OFFLINE_FALLBACK
    except Exception as e:
        print(f"⚠️ Error grabbing EXPTV: {e}")
        return OFFLINE_FALLBACK

# -------- Grab EXPTV schedule (today only) --------
def grab_schedule():
    today = datetime.now(TIMEZONE).strftime("%A").lower()
    url = f"https://exptv.org/js/{today}-3.js?v=001"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        matches = re.findall(r'\["([^"]+)",\s*"([^"]+)"\]', r.text)
        schedule = [(t, title) for t, title in matches]
        print(f"✅ Parsed {len(schedule)} EPG entries for {today.capitalize()}")
        return schedule
    except Exception as e:
        print(f"⚠️ Could not grab schedule: {e}")
        return []

# -------- Write M3U --------
def write_m3u(stream_url: str):
    epg_url = "https://raw.githubusercontent.com/electricmittens-lab/StreamsToM3U8/main/exp.xml"
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
        f.write(f'#EXTINF:-1 tvg-id="exptv" tvg-name="EXPTV" tvg-logo="{EXPTV_LOGO}", EXPTV\n')
        f.write(stream_url + "\n")
    print(f"✅ Wrote playlist to {OUTPUT_M3U}")

# -------- Write XMLTV --------
def write_xml(schedule):
    tv = etree.Element("tv")
    channel = etree.SubElement(tv, "channel", id="exptv")
    etree.SubElement(channel, "display-name").text = "EXPTV"
    etree.SubElement(channel, "icon", src=EXPTV_LOGO)

    if schedule:
        today = datetime.now(TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        dt_format = "%Y%m%d%H%M%S %z"

        for idx, (time_str, title) in enumerate(schedule):
            try:
                t = datetime.strptime(time_str, "%I:%M %p").time()
                start_dt = today.replace(hour=t.hour, minute=t.minute)
                if idx + 1 < len(schedule):
                    nt = datetime.strptime(schedule[idx + 1][0], "%I:%M %p").time()
                    stop_dt = today.replace(hour=nt.hour, minute=nt.minute)
                else:
                    stop_dt = today + timedelta(days=1)

                prog = etree.SubElement(tv, "programme")
                prog.set("channel", "exptv")
                prog.set("start", start_dt.strftime(dt_format))
                prog.set("stop", stop_dt.strftime(dt_format))

                etree.SubElement(prog, "title", lang="en").text = title
            except Exception as e:
                print(f"⚠️ Failed to parse EPG entry {time_str}, {title}: {e}")

    xml_bytes = etree.tostring(tv, pretty_print=True, encoding="utf-8")
    with open(OUTPUT_XML, "wb") as f:
        f.write(xml_bytes)
    print(f"✅ Wrote XMLTV to {OUTPUT_XML}")

# -------- Main --------
if __name__ == "__main__":
    stream_url = grab_exptv()
    schedule = grab_schedule()
    write_m3u(stream_url)
    write_xml(schedule)
