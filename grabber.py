def grab_exptv_via_list_js():
    """
    Fetch https://exptv.org/js/list.js and scan for .mp4 links.
    """
    js_url = "https://exptv.org/js/list.js"
    headers = {
        "Referer": "https://exptv.org/css/video.css?v=2.1",
        "User-Agent": "Mozilla/5.0 (compatible; EXPTVGrabber/1.0)"
    }
    try:
        r = requests.get(js_url, headers=headers, timeout=15)
        r.raise_for_status()
        import re
        matches = re.findall(r'https?://[^"\']+\.mp4', r.text)
        if matches:
            return matches[0]  # or logic to pick the “current” one
        else:
            print("⚠️ list.js: no .mp4 found")
            return None
    except Exception as e:
        print(f"⚠️ list.js error: {e}")
        return None
