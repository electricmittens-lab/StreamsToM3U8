#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from lxml import etree

# -------- Settings --------
OUTPUT_M3U = "exp.m3u"
OUTPUT_XML = "exp.xml"
OFFLINE_FALLBACK = "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4"
EXPTV_URL = "https://exptv.org"
EXPTV_LOGO = "logo.png"  # or full URL to their logo if you prefer
# --------------------------

# -------- Grab EXPTV stream --------
def grab_exptv():
    try:
        r = requests.get(EXPTV_URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Look for the <source> element with type video/mp4
        tag = soup.find("source", {"type": "video/mp4"})
        if not tag or not tag.has_attr("src"):
            print("⚠️ Could not find EXPTV <source> tag, using fallback.")
            return OFFLINE_FALLBACK

        # Clean up the link (strip off any #t= time markers)
        url = tag["src"].split("#")[0]
        print(f"✅ Found EXPTV stream: {url}")
        return url

    except Exception as e:
        print(f"⚠️ Error grabbing EXPTV: {e}")
        return OFFLINE_FALLBACK


# -------- Write M3U --------
def write_m3u(stream_url: str):
    epg_url = "https://raw.githubusercontent.com/electricmittens-lab/StreamsToM3U8/main/exp.xml"
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
        f.write(f'#EXTINF:-1 tvg-id="exptv" tvg-name="EXPTV" tvg-logo="{EXPTV_LOGO}", EXPTV\n')
        f.write(stream_url + "\n")
    print(f"✅ Wrote playlist to {OUTPUT_M3U}")


# -------- Write XMLTV (empty shell for EXPTV) --------
def write_xml():
    tv = etree.Element("tv")
    channel = etree.SubElement(tv, "channel", id="exptv")
    etree.SubElement(channel, "display-name").text = "EXPTV"
    etree.SubElement(channel, "icon", src=EXPTV_LOGO)

    xml_bytes = etree.tostring(tv, pretty_print=True, encoding="utf-8")
    with open(OUTPUT_XML, "wb") as f:
        f.write(xml_bytes)
    print(f"✅ Wrote XMLTV to {OUTPUT_XML}")


# -------- Main --------
if __name__ == "__main__":
    stream_url = grab_exptv()
    write_m3u(stream_url)
    write_xml()
