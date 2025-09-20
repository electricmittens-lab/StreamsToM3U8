#! /usr/bin/python3
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

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
HTTP_TIMEOUT = 15
HEADERS = {
    # Pretend to be a normal desktop browser so sites return full HTML
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
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
    """
    streams: list of dicts with keys: name, id, category, desc, logo, url
    """
    data = etree.Element("tv")
    data.set("generator-info-name", "youtube-live-epg")
    data.set("generator-info-url", "https://github.com/dp247/YouTubeToM3U8")

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

    return etree.tostring(data, pretty_print=True)
