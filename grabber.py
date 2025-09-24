def grab_exptv():
    try:
        r = requests.get(EXPTV_URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # First try the id-based selector
        tag = soup.find("source", {"id": "mp4_src"})
        if not tag or not tag.has_attr("src"):
            # Fallback: grab *any* source with .mp4
            tag = soup.find("source", {"type": "video/mp4"})

        if not tag or not tag.has_attr("src"):
            print("⚠️ Could not find EXPTV <source> tag, using fallback.")
            return OFFLINE_FALLBACK

        url = tag["src"].split("#")[0]  # strip #t= marker
        print(f"✅ Found EXPTV stream: {url}")
        return url

    except Exception as e:
        print(f"⚠️ Error grabbing EXPTV: {e}")
        return OFFLINE_FALLBACK
