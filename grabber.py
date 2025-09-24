#! /usr/bin/python3
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
import requests
from lxml import etree
from bs4 import BeautifulSoup

# -------- Settings --------
tz = pytz.timezone("Europe/London")
EXTRA_M3U = "m3u.m3u"         # prepended first if present
OUTPUT_M3U = "murdercapital.m3u"
EPG_XML = "epg.xml"
TWITCH_FALLBACK_LOGO = "https://static-cdn.jtvnw.net/ttv-static-metadata/twitch_logo3.jpg"
OFFLINE_FALLBACK = "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4"
EXPTV_LOGO = "https://raw.githubusercontent.com/electricmittens-lab/StreamsToM3U8/main/logo.png"
HTTP_TIMEOUT = 15
# --------------------------

channels = []  # list[dict]: {"name","id","category","desc","logo","url"}


def generate_times(curr_dt: datetime):
    """Return 3-hourly start/stop times (XMLTV)."""
    last_hour = curr_dt.replace(microsecond=0, second=0, minute=0)
    last_hour = tz.localize(last_hour)
    start_dates = [last_hour]
    for _ in range(7):
        last_hour += timedelta(hours=3)
        start_dates.append(last_hour)
    end_dates = start_dates[1:]
    end_dates.append(start_dates[-1] + timedelta(hours=3))
    return start_dates, end_dates


def build_xml_tv(streams: list) -> bytes:
    data = etree.Element("tv")
    data.set("generator-info-name", "m3u-grabber")
    data.set("generator-info-url", "https://github.com/electricmittens-lab/StreamsToM3U8")

    for s in streams:
        channel = etree.SubElement(data, "channel")
        channel.set("id", s.get("id", s["name"]))
        name = etree.SubElement(channel, "display-name")
        name.set("lang", "en")
        name.text = s["name"]

        dt_format = "%Y%m%d%H%M%S %z"
        start_dates, end_dates = generate_times(datetime.now())
        for idx, val in enumerate(start_dates):
            programme = etree.SubElement(data, "programme")
            programme.set("channel", s.get("id", s["name"]))
            programme.set("start", val.strftime(dt_format))
            programme.set("stop", end_dates[idx].strftime(dt_format))

            title = etree.SubElement(programme, "title")
            title.set("lang", "en")
            title.text = f"LIVE: {s['name']}"

            description = etree.SubElement(programme, "desc")
            description.set("lang", "en")
            description.text = s.get("desc") or "No description provided"

            logo = s.get("logo")
            if logo:
                icon = etree.SubElement(programme, "icon")
                icon.set("src", logo)

    return etree.tostring(data, pretty_print=True, encoding="utf-8")


# -------- Helpers --------
def _meta(soup, prop, default=""):
    tag = soup.find("meta", property=prop)
    return tag["content"] if tag and tag.has_attr("content") else default


def _append_channel(name, cid, category, desc, logo, url):
    channels.append({
        "name": name,
        "id": cid,
        "category": category,
        "desc": desc,
        "logo": logo,
        "url": url
    })


# -------- Grabbers --------
def grab_exptv():
    """
    Always include EXPTV channel first. Scrapes current .mp4 from exptv.org or uses fallback.
    Uses a hard-coded logo from your repo.
    """
    name = "EXPTV"
    cid = "exptv"
    category = "Variety"

    try:
        r = requests.get("https://exptv.org/", timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            print("⚠️ EXPTV bad response, using fallback")
            return {
                "name": name,
                "id": cid,
                "category": category,
                "desc": "EXPTV offline",
                "logo": EXPTV_LOGO,
                "url": OFFLINE_FALLBACK,
            }

        soup = BeautifulSoup(r.text, "html.parser")

        # Look for <source src="...mp4">
        mp4_url = None
        for tag in soup.find_all("source"):
            src = tag.get("src")
            if src and src.endswith(".mp4"):
                mp4_url = src
                break

        if not mp4_url:
            # fallback: naive scan
            for line in r.text.splitlines():
                if ".mp4" in line:
                    start = line.find("http")
                    end = line.find(".mp4") + 4
                    mp4_url = line[start:end]
                    break

        if not mp4_url:
            print("⚠️ EXPTV no .mp4 found, using fallback")
            mp4_url = OFFLINE_FALLBACK

        desc = _meta(soup, "og:description", "No description")

        print(f"✅ EXPTV added → {mp4_url}")
        return {
            "name": name,
            "id": cid,
            "category": category,
            "desc": desc,
            "logo": EXPTV_LOGO,
            "url": mp4_url,
        }

    except Exception as e:
        print(f"⚠️ EXPTV error: {e}")
        return {
            "name": name,
            "id": cid,
            "category": category,
            "desc": "EXPTV error",
            "logo": EXPTV_LOGO,
            "url": OFFLINE_FALLBACK,
        }


# -------- Main parse --------
channel_name = ""
channel_id = ""
category = ""

with open("./streams.txt", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("##"):
            continue
        if not (line.startswith("https:") or line.startswith("http:")):
            parts = [x.strip() for x in line.split("||")]
            if len(parts) < 3:
                print(f"⚠️ Bad metadata line (need Name || ID || Category): {line}")
                channel_name, channel_id, category = "", "", ""
                continue
            channel_name, channel_id, category = parts[0], parts[1], parts[2].title()
        else:
            netloc = urlparse(line).netloc.lower()
            # (You still have Twitch, YouTube, Dailymotion grabbers here)
            if "twitch.tv" in netloc:
                # your grab_twitch() function
                pass
            elif "youtube.com" in netloc:
                # your grab_youtube() function
                pass
            elif "dailymotion.com" in netloc:
                # your grab_dailymotion() function
                pass
            else:
                print(f"⚠️ Unknown provider for {channel_name}: {line}")

# -------- Always include EXPTV first --------
exptv_channel = grab_exptv()
if exptv_channel:
    channels.insert(0, exptv_channel)

# -------- Write M3U (prepend m3u.m3u first) --------
with open(OUTPUT_M3U, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")

    if os.path.exists(EXTRA_M3U):
        with open(EXTRA_M3U, "r", encoding="utf-8") as extra:
            for line in extra:
                if not line.strip().startswith("#EXTM3U"):
                    out.write(line)

    for s in channels:
        name = s["name"]
        logo = s.get("logo", "")
        url = s["url"]
        if logo:
            out.write(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}", {name}\n')
        else:
            out.write(f'#EXTINF:-1 tvg-name="{name}", {name}\n')
        out.write(f"{url}\n")

print(f"✅ Merged playlist written to {OUTPUT_M3U}")

# -------- Write XMLTV --------
xml_bytes = build_xml_tv(channels)
with open(EPG_XML, "wb") as xf:
    xf.write(xml_bytes)
print(f"✅ EPG written to {EPG_XML}")
