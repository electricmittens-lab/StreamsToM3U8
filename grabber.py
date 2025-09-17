#! /usr/bin/python3
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytz
import requests
from lxml import etree
from bs4 import BeautifulSoup

tz = pytz.timezone('Europe/London')
channels = []


def generate_times(curr_dt: datetime):
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
    data.set("generator-info-name", "youtube-live-epg")
    data.set("generator-info-url", "https://github.com/dp247/YouTubeToM3U8")

    for stream in streams:
        channel = etree.SubElement(data, "channel")
        channel.set("id", stream[1])
        name = etree.SubElement(channel, "display-name")
        name.set("lang", "en")
        name.text = stream[0]

        dt_format = "%Y%m%d%H%M%S %z"
        start_dates, end_dates = generate_times(datetime.now())

        for idx, val in enumerate(start_dates):
            programme = etree.SubElement(data, "programme")
            programme.set("channel", stream[1])
            programme.set("start", val.strftime(dt_format))
            programme.set("stop", end_dates[idx].strftime(dt_format))

            title = etree.SubElement(programme, "title")
            title.set("lang", "en")
            title.text = f"LIVE: {stream[0]}"

            description = etree.SubElement(programme, "desc")
            description.set("lang", "en")
            description.text = stream[3] if stream[3] else "No description provided"

            if stream[4]:
                icon = etree.SubElement(programme, "icon")
                icon.set("src", stream[4])

    return etree.tostring(data, pretty_print=True, encoding="utf-8")


# --- Grabbers ---
def grab_youtube(url: str, channel_name, channel_id, category):
    if "&" in url:
        url = url.split("&")[0]

    try:
        stream_info = requests.get(url, timeout=15)
        soup = BeautifulSoup(stream_info.text, features="html.parser")

        if stream_info.status_code != 200 or ".m3u8" not in stream_info.text:
            print(f"⚠️ Skipped YouTube channel: {channel_name} (no stream found)")
            return None

        end = stream_info.text.find(".m3u8") + 5
        tuner = 100
        while True:
            if "https://" in stream_info.text[end - tuner: end]:
                link = stream_info.text[end - tuner: end]
                start = link.find("https://")
                end = link.find(".m3u8") + 5

                stream_desc = soup.find("meta", property="og:description")["content"]
                stream_image_url = soup.find("meta", property="og:image")["content"]

                return (
                    channel_name,
                    channel_id,
                    category,
                    stream_desc,
                    stream_image_url,
                    link[start:end],
                )
            else:
                tuner += 5
    except Exception as e:
        print(f"⚠️ Error grabbing YouTube {channel_name}: {e}")
        return None


def grab_dailymotion(url: str, channel_name, channel_id, category):
    try:
        stream_info = requests.get(url, timeout=15)
        if stream_info.status_code != 200:
            print(f"⚠️ Skipped Dailymotion channel: {channel_name} (no stream found)")
            return None

        soup = BeautifulSoup(stream_info.text, features="html.parser")

        stream_desc = soup.find("meta", property="og:description")["content"]
        stream_image_url = soup.find("meta", property="og:image")["content"]

        stream_api = requests.get(
            f"https://www.dailymotion.com/player/metadata/video/{url.split('/')[4]}"
        ).json()["qualities"]["auto"][0]["url"]

        m3u_file = requests.get(stream_api).text.strip().split("\n")[1:]
        best_url = sorted(
            [
                [int(m3u_file[i].split(",")[2].split("=")[1]), m3u_file[i + 1]]
                for i in range(0, len(m3u_file) - 1, 2)
            ],
            key=lambda x: x[0],
        )[-1][1].split("#")[0]

        return (
            channel_name,
            channel_id,
            category,
            stream_desc,
            stream_image_url,
            best_url,
        )
    except Exception as e:
        print(f"⚠️ Error grabbing Dailymotion {channel_name}: {e}")
        return None


def grab_twitch(url: str, channel_name, channel_id, category):
    try:
        stream_info = requests.get(url, timeout=15)
        if stream_info.status_code != 200:
            print(f"⚠️ Skipped Twitch channel: {channel_name} (bad response)")
            return (
                channel_name,
                channel_id,
                category,
                "No description",
                "",
                "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4",
            )

        soup = BeautifulSoup(stream_info.text, features="html.parser")

        stream_desc = soup.find("meta", property="og:description")
        stream_desc = stream_desc["content"] if stream_desc else "No description"

        stream_image_url = soup.find("meta", property="og:image")
        stream_image_url = stream_image_url["content"] if stream_image_url else ""

        response = requests.get(f"https://pwn.sh/tools/streamapi.py?url={url}").json()
        url_list = response.get("urls", {})

        if not url_list:
            # fallback if Twitch is offline or URL expired
            stream_url = "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4"
        else:
            max_res_key = list(url_list)[-1]
            stream_url = url_list.get(max_res_key)

        return (
            channel_name,
            channel_id,
            category,
            stream_desc,
            stream_image_url,
            stream_url,
        )
    except Exception as e:
        print(f"⚠️ Error grabbing Twitch {channel_name}: {e}")
        return (
            channel_name,
            channel_id,
            category,
            "No description",
            "",
            "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4",
        )


# --- Main ---
channel_name = ""
channel_id = ""
category = ""

with open("./streams.txt", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("##"):
            continue
        if not (line.startswith("https:") or line.startswith("http:")):
            line = line.split("||")
            channel_name = line[0].strip()
            channel_id = line[1].strip()
            category = line[2].strip().title()
        else:
            netloc = urlparse(line).netloc
            result = None
            if "youtube.com" in netloc:
                result = grab_youtube(line, channel_name, channel_id, category)
            elif "dailymotion.com" in netloc:
                result = grab_dailymotion(line, channel_name, channel_id, category)
            elif "twitch.tv" in netloc:
                result = grab_twitch(line, channel_name, channel_id, category)

            if result:
                channels.append(result)


# --- Output merged M3U ---
output_file = "murdercapital.m3u"
extra_file = "m3u.m3u"  # prepend this file if it exists

with open(output_file, "w", encoding="utf-8") as out:
    out.write("#EXTM3U\n")

    # First include m3u.m3u if it exists
    if os.path.exists(extra_file):
        with open(extra_file, "r", encoding="utf-8") as extra:
            for line in extra:
                if not line.strip().startswith("#EXTM3U"):
                    out.write(line)

    # Then add scraped channels with their profile image as logo
    for ch in channels:
        name, cid, category, desc, logo, url = ch
        if logo:
            out.write(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}", {name}\n')
        else:
            out.write(f'#EXTINF:-1 tvg-name="{name}", {name}\n')
        out.write(f"{url}\n")

print(f"✅ Merged playlist written to {output_file}")

# --- Output XMLTV ---
channel_xml = build_xml_tv(channels)
with open("epg.xml", "wb") as f:
    f.write(channel_xml)

# --- Cleanup ---
if "temp.txt" in os.listdir():
    os.remove("temp.txt")
    for f in os.listdir():
        if f.startswith("watch"):
            os.remove(f)
