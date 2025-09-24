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
EXPTV_URL = "https://exptv.org/"
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
        start_dat_
