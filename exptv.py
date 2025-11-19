import requests
import re
import datetime
import subprocess
import time

WEEKMAP = [
    "monday-3.js", "tuesday-3.js", "wednesday-3.js",
    "thursday-3.js", "friday-3.js", "saturday-3.js", "sunday-3.js"
]

def get_current_block():
    now = datetime.datetime.now()
    weekday = now.weekday()  # 0 = Monday
    hour = now.hour
    minute = now.minute
    block = "b1" if minute < 30 else "b2"
    block_min = minute if block == "b1" else minute - 30
    day_js_url = f"https://exptv.org/js/{WEEKMAP[weekday]}"
    list_js_url = "https://exptv.org/js/list.js"

    # Fetch schedule JS
    day_js = requests.get(day_js_url).text
    blockname = f"{WEEKMAP[weekday][:3]}_{hour:02d}_{block}"

    # Find block variable → program object name
    m = re.search(rf'var {blockname}\s*=\s*(\w+);', day_js)
    prog_obj = m.group(1) if m else None

    # Find MP4 filename in list.js
    list_js = requests.get(list_js_url).text
    m2 = re.search(rf'var {prog_obj}\s*=\s*\{{[^}}]*file\s*:\s*"(.*?)"', list_js)
    filename = m2.group(1) if m2 else None

    return {
        "filename": filename,
        "offset": block_min * 60,  # seconds into block
        "blockname": blockname,
        "title": prog_obj,
        "now": now
    }

def stream_to_youtube(youtube_url):
    while True:
        info = get_current_block()
        if not info or not info["filename"]:
            print("Could not determine current block. Retrying in 60s...")
            time.sleep(60)
            continue
        mp4_url = f"https://exptv.org/content2/{info['filename']}"
        seek_offset = info['offset']
        print(f"Streaming: {mp4_url} ({info['title']}) starting at {seek_offset}s ({info['blockname']})")
        # Note: Some ffmpeg builds ignore #t= fragment; use -ss for accurate start
        cmd = [
            "ffmpeg", "-re",
            "-ss", str(seek_offset),
            "-i", mp4_url,
            "-c", "copy",
            "-f", "flv",
            youtube_url
        ]
        cp = subprocess.Popen(cmd)
        # Play for remaining seconds in the block, then kill ffmpeg and update
        now_min = info["now"].minute % 30
        remain = (30 - now_min) * 60
        try:
            time.sleep(remain)
        except KeyboardInterrupt:
            cp.terminate()
            break
        cp.terminate()
        print("Switching to next block...")

yt_rtmp = "rtmp://a.rtmp.youtube.com/live2/m9wq-1m35-rqhw-0s8s-a32y"
stream_to_youtube(yt_rtmp)
