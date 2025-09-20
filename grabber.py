#!/usr/bin/env python3
import os
import subprocess
from lxml import etree

# -------- Settings --------
OUTPUT_M3U = "streams.m3u"
EXTRA_FILE = "streams.txt"
# --------------------------

channels = []  # list of {"name","id","category","url"}


# --- YOUTUBE RESOLVER ---
def resolve_youtube(url: str) -> str | None:
    """
    Resolve a YouTube watch/live URL into a single best-quality HLS URL.
    Returns one URL string or None.
    """
    try:
        print(f"[YouTube Resolver] Resolving {url} ...")
        result = subprocess.check_output(
            ["yt-dlp", "-f", "best", "-g", url],
            stderr=subprocess.STDOUT
        )
        stream_url = result.decode().strip().split("\n")[0]
        print(f"[YouTube Resolver] Found URL: {stream_url[:60]}...")
        return stream_url
    except Exception as e:
        print(f"[YouTube Resolver] Failed: {e}")
        return None


# --- LOAD STREAMS.TXT ---
def load_streams():
    global channels
    if not os.path.exists(EXTRA_FILE):
        print(f"[Error] {EXTRA_FILE} not found")
        return
    with open(EXTRA_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    for i in range(0, len(lines), 2):
        try:
            meta = lines[i].split("||")
            url = lines[i + 1].strip()

            if len(meta) >= 3:
                name, id_, category = [m.strip() for m in meta[:3]]
            else:
                name, id_, category = meta[0].strip(), meta[0].strip(), "Misc"

            # --- Resolve YouTube links automatically ---
            if "youtube.com" in url or "youtu.be" in url:
                resolved = resolve_youtube(url)
                if resolved:
                    url = resolved
                else:
                    print(f"[Warning] Could not resolve YouTube URL: {url}")

            channels.append({
                "name": name,
                "id": id_,
                "category": category,
                "url": url
            })

        except Exception as e:
            print(f"[Error] parsing streams.txt entry: {e}")


# --- BUILD M3U ---
def build_m3u():
    lines = ["#EXTM3U"]
    for ch in channels:
        if not ch["url"]:
            continue
        lines.append(
            f'#EXTINF:-1 tvg-id="{ch["id"]}" group-title="{ch["category"]}", {ch["name"]}'
        )
        lines.append(ch["url"])
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Playlist written to {OUTPUT_M3U}")


# --- BUILD EPG ---
def build_epg():
    root = etree.Element("tv")
    for ch in channels:
        ch_el = etree.SubElement(root, "channel", id=ch["id"])
        etree.SubElement(ch_el, "display-name").text = ch["name"]

    xml = etree.tostring(root, pretty_print=True, encoding="unicode")
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml)
    print("✅ EPG written to epg.xml")


# --- MAIN ---
if __name__ == "__main__":
    load_streams()
    build_m3u()
    build_epg()
