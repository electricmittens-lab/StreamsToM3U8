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
def grab_youtube(url, name, cid, category):
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        if r.status_code != 200 or ".m3u8" not in r.text:
            print(f"⚠️ Skipped YouTube: {name} (no .m3u8 found)")
            return
        soup = BeautifulSoup(r.text, "html.parser")

        # naive scan for m3u8
        end = r.text.find(".m3u8") + 5
        tuner = 100
        stream_url = None
        while True:
            if "https://" in r.text[end - tuner:end]:
                link = r.text[end - tuner:end]
                start = link.find("https://")
                end2 = link.find(".m3u8") + 5
                stream_url = link[start:end2]
                break
            tuner += 5
            if tuner > 5000:
                break

        if not stream_url:
            print(f"⚠️ Skipped YouTube: {name} (failed to extract m3u8 url)")
            return

        desc = _meta(soup, "og:description", "")
        logo = _meta(soup, "og:image", "")
        _append_channel(name, cid, category, desc, logo, stream_url)
        print(f"✅ YouTube: {name} (logo from og:image)")
    except Exception as e:
        print(f"⚠️ YouTube error {name}: {e}")


def grab_dailymotion(url, name, cid, category):
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            print(f"⚠️ Skipped Dailymotion: {name} (bad response)")
            return
        soup = BeautifulSoup(r.text, "html.parser")

        desc = _meta(soup, "og:description", "")
        logo = _meta(soup, "og:image", "")

        meta = requests.get(
            f"https://www.dailymotion.com/player/metadata/video/{url.split('/')[4]}",
            timeout=HTTP_TIMEOUT
        ).json()
        api_m3u = meta["qualities"]["auto"][0]["url"]

        m3u_text = requests.get(api_m3u, timeout=HTTP_TIMEOUT).text.strip().split("\n")[1:]
        pairs = []
        for i in range(0, len(m3u_text) - 1, 2):
            try:
                bw = int(m3u_text[i].split(",")[2].split("=")[1])
                pairs.append([bw, m3u_text[i + 1]])
            except Exception:
                pass
        if not pairs:
            print(f"⚠️ Skipped Dailymotion: {name} (no qualities)")
            return

        best_url = sorted(pairs, key=lambda x: x[0])[-1][1].split("#")[0]
        _append_channel(name, cid, category, desc, logo, best_url)
        print(f"✅ Dailymotion: {name} (logo from og:image)")
    except Exception as e:
        print(f"⚠️ Dailymotion error {name}: {e}")


def _twitch_handle_from_url(url: str, fallback: str) -> str:
    handle = urlparse(url).path.strip("/").split("/")[0].lower()
    if not handle:
        handle = fallback.lower().replace(" ", "")
    return handle


def _twitch_avatar(handle: str) -> str:
    """Try two public sources to get the real Twitch profile image."""
    # 1) decapi.me (simple text URL)
    try:
        r = requests.get(f"https://decapi.me/twitch/avatar/{handle}", timeout=10)
        if r.status_code == 200 and r.text.startswith("http"):
            print(f"   → Twitch avatar via decapi: {handle}")
            return r.text.strip()
    except Exception:
        pass

    # 2) ivr.fi public API (JSON), needs a UA
    try:
        r = requests.get(
            f"https://api.ivr.fi/v2/twitch/user?login={handle}",
            headers={"User-Agent": "murdercapital/1.0 (+https://example.local)"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            # ivr.fi returns a list or a dict depending on query
            if isinstance(data, list) and data:
                url = data[0].get("logo") or data[0].get("profile_image_url")
                if url and url.startswith("http"):
                    print(f"   → Twitch avatar via ivr.fi: {handle}")
                    return url
            elif isinstance(data, dict):
                url = data.get("logo") or data.get("profile_image_url")
                if url and url.startswith("http"):
                    print(f"   → Twitch avatar via ivr.fi: {handle}")
                    return url
    except Exception:
        pass

    print(f"   → Twitch avatar fallback (generic): {handle}")
    return TWITCH_FALLBACK_LOGO


def grab_twitch(url, name, cid, category):
    """
    Always append channel:
      - Resolve real profile image via decapi/ivr.fi
      - Resolve stream via pwn.sh; fallback to OFFLINE_FALLBACK
    """
    try:
        handle = _twitch_handle_from_url(url, fallback=name)
        logo = _twitch_avatar(handle)

        # optional description via page meta (ignore failures)
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT)
            soup = BeautifulSoup(r.text, "html.parser")
            desc = _meta(soup, "og:description", "No description")
        except Exception:
            desc = "No description"

        # resolve stream URL via pwn.sh
        try:
            resp = requests.get(f"https://pwn.sh/tools/streamapi.py?url={url}", timeout=HTTP_TIMEOUT).json()
            url_list = resp.get("urls", {})
        except Exception:
            url_list = {}

        if not url_list:
            stream_url = OFFLINE_FALLBACK
            print(f"⚠️ Twitch offline/expired: {name} → using fallback stream")
        else:
            max_res_key = list(url_list)[-1]
            stream_url = url_list.get(max_res_key) or OFFLINE_FALLBACK

        _append_channel(name, cid, category, desc, logo, stream_url)
        print(f"✅ Twitch: {name} (logo for @{handle})")

    except Exception as e:
        print(f"⚠️ Twitch error {name}: {e}")
        _append_channel(name, cid, category, "No description", TWITCH_FALLBACK_LOGO, OFFLINE_FALLBACK)


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
            # metadata line
            parts = [x.strip() for x in line.split("||")]
            if len(parts) < 3:
                print(f"⚠️ Bad metadata line (need Name || ID || Category): {line}")
                channel_name, channel_id, category = "", "", ""
                continue
            channel_name, channel_id, category = parts[0], parts[1], parts[2].title()
        else:
            # URL line
            netloc = urlparse(line).netloc.lower()
            if "youtube.com" in netloc:
                grab_youtube(line, channel_name, channel_id, category)
            elif "dailymotion.com" in netloc:
                grab_dailymotion(line, channel_name, channel_id, category)
            elif "twitch.tv" in netloc:
                grab_twitch(line, channel_name, channel_id, category)
            else:
                print(f"⚠️ Unknown provider for {channel_name}: {line}")


# -------- Write M3U (prepend m3u.m3u first) --------
with open(OUTPUT_M3U, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")

    # prepend curated list
    if os.path.exists(EXTRA_M3U):
        with open(EXTRA_M3U, "r", encoding="utf-8") as extra:
            for line in extra:
                if not line.strip().startswith("#EXTM3U"):
                    out.write(line)

    # then generated channels (profile logo in tvg-logo)
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

# -------- Cleanup (optional) --------
if "temp.txt" in os.listdir():
    try:
        os.remove("temp.txt")
        for fname in list(os.listdir()):
            if fname.startswith("watch"):
                os.remove(fname)
    except Exception:
        pass
