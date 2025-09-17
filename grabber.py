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
                "https://static-cdn.jtvnw.net/ttv-static-metadata/twitch_logo3.jpg",
                "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4",
            )

        soup = BeautifulSoup(stream_info.text, features="html.parser")

        # description (optional for XML)
        desc_tag = soup.find("meta", property="og:description")
        stream_desc = desc_tag["content"] if desc_tag else "No description"

        # ✅ derive twitch handle from URL for real profile image
        handle = urlparse(url).path.strip("/").split("/")[0].lower()  # e.g. "exptv_"
        if not handle:
            # last-resort fallback if URL parsing failed
            handle = (channel_id or channel_name.replace(" ", "")).lower()

        # get real Twitch profile avatar (no OAuth)
        try:
            avatar_resp = requests.get(f"https://decapi.me/twitch/avatar/{handle}", timeout=10)
            if avatar_resp.status_code == 200 and avatar_resp.text.startswith("http"):
                stream_image_url = avatar_resp.text.strip()
            else:
                stream_image_url = "https://static-cdn.jtvnw.net/ttv-static-metadata/twitch_logo3.jpg"
        except Exception:
            stream_image_url = "https://static-cdn.jtvnw.net/ttv-static-metadata/twitch_logo3.jpg"

        # resolve stream URL via pwn.sh (may be empty/offline/ephemeral)
        try:
            response = requests.get(f"https://pwn.sh/tools/streamapi.py?url={url}", timeout=15).json()
            url_list = response.get("urls", {})
        except Exception:
            url_list = {}

        if not url_list:
            # stable fallback when offline/expired
            stream_url = "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4"
        else:
            # pick highest available resolution (last key is typically highest)
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
            "https://static-cdn.jtvnw.net/ttv-static-metadata/twitch_logo3.jpg",
            "https://github.com/ExperiencersInternational/tvsetup/raw/main/staticch/no_stream_2.mp4",
        )
