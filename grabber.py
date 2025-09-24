#!/usr/bin/env python3
import requests, re
from bs4 import BeautifulSoup

# -------- Settings --------
OUTPUT_M3U = "murdercapital.m3u"
EXPTV_LOGO = "logo.png"  # replace with path to your repo logo if desired
HTTP_TIMEOUT = 15

HEADERS = {
    "Referer": "https://exptv.org/css/video.css?v=2.1",
    "User-Agent": "Mozilla/5.0 (compatible; EXPTVGrabber/1.0)"
}

# -------- JS Parsers --------
def grab_exptv_via_main_js():
    url = "https://exptv.org/js/main.js?v=005"
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        matches = re.findall(r'https?://[^"\']+\.mp4', r.text)
        if matches:
            return matches[0]
    except Exception as e:
        print(f"⚠️ main.js error: {e}")
    return None

def grab_exptv_via_list_js():
    url = "https://exptv.org/js/list.js"
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        matches = re.findall(r'https?://[^"\']+\.mp4', r.text)
        if matches:
            return matches[0]
    except Exception as e:
        print(f"⚠️ list.js error: {e}")
    return None

# -------- HTML Parser --------
def grab_exptv_via_html():
    url = "https://exptv.org/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # <source src="...mp4">
        for tag in soup.find_all("source"):
            src = tag.get("src")
            if src and src.endswith(".mp4"):
                return src

        # Raw .mp4 in HTML
        for line in r.text.splitlines():
            if ".mp4" in line:
                a = line.find("http")
                b = line.find(".mp4")
                if a != -1 and b != -1:
                    return line[a:b+4]

    except Exception as e:
        print(f"⚠️ HTML error: {e}")
    return None

# -------- Combined grabber --------
def grab_exptv_url():
    for grab in (grab_exptv_via_main_js, grab_exptv_via_list_js, grab_exptv_via_html):
        url = grab()
        if url:
            print(f"✅ EXPTV found: {url}")
            return url
    print("⚠️ EXPTV: no mp4 found, offline fallback")
    return None

# -------- Write playlist --------
def write_m3u(url: str):
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if url:
            f.write(f'#EXTINF:-1 tvg-id="exptv" tvg-name="EXPTV" tvg-logo="{EXPTV_LOGO}", EXPTV\n')
            f.write(url + "\n")
        else:
            # offline fallback (optional)
            f.write('#EXTINF:-1 tvg-id="exptv" tvg-name="EXPTV", EXPTV (offline)\n')
            f.write("https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4\n")

if __name__ == "__main__":
    mp4 = grab_exptv_url()
    write_m3u(mp4)
