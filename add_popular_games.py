import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

CDN_BASE_URL = "https://cdn.jsdelivr.net/gh/nukIeer/gameshieldcdn@master/games"
GAMES_JSON_PATH = "games.json"

# Ordered list: items earlier are placed earlier in games.json.
POPULAR_TARGETS: List[Tuple[str, List[str]]] = [
    ("roblox", ["roblox"]),
    ("discord", ["discord-chat-for-gamers", "discord"]),
    ("pubg", ["pubg-mobile", "pubg-mobile-kr", "pubg-mobile-lite"]),
    ("minecraft", ["minecraft-pocket-edition-2018", "minecraft-pocket-edition", "minecraft"]),
    ("subway", ["subway-surfers", "subway-surfers-1"]),
    ("temple", ["temple-run", "temple-run-2"]),
    ("sonic", ["sonic-dash", "sonic-the-hedgehog"]),
]


def format_size(bytes_size: int) -> str:
    if not bytes_size:
        return "N/A"
    return f"{round(bytes_size / (1024 * 1024), 1)}MB"


def format_downloads(count: int) -> str:
    if not count:
        return "N/A"
    if count >= 1_000_000_000:
        return f"{count // 1_000_000_000}B+"
    if count >= 1_000_000:
        return f"{count // 1_000_000}M+"
    if count >= 1_000:
        return f"{count // 1_000}K+"
    return str(count)


def get_game_details(uname: str) -> Optional[dict]:
    url = f"https://{uname}.en.aptoide.com/app"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return None

        data = json.loads(script.string)
        app_data = data.get("props", {}).get("pageProps", {}).get("app", {})
        return app_data if app_data else None
    except Exception:
        return None


def download_image(url: str, filepath: str) -> bool:
    if not url:
        return False

    try:
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code != 200:
            return False

        with open(filepath, "wb") as f:
            for chunk in r.iter_content(1024):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def normalize_ext(url: str) -> str:
    m = re.search(r"\.([a-zA-Z0-9]{3,4})(?:\?|$)", url or "")
    if not m:
        return "jpg"
    ext = m.group(1).lower()
    if ext == "jpeg":
        return "jpg"
    if ext in {"jpg", "png", "webp"}:
        return ext
    return "jpg"


def build_game_info(game_id: str, app_data: dict) -> dict:
    package = app_data.get("package", "")
    title = app_data.get("name", game_id)
    desc = app_data.get("media", {}).get("description", "No description available")
    whats_new = app_data.get("media", {}).get("news", "No update notes")

    rating = app_data.get("stats", {}).get("prating", {}).get("avg", "N/A")
    raw_downloads = app_data.get("stats", {}).get("pdownloads", 0)
    version = app_data.get("file", {}).get("vername", "N/A")
    android_v = app_data.get("hardware", {}).get("version", {}).get("number", "N/A")
    age = app_data.get("age", {}).get("pegi", "N/A")

    size_bytes = app_data.get("size") or app_data.get("file", {}).get("filesize", 0)

    game_dir = os.path.join("games", game_id)
    screenshots_dir = os.path.join(game_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    icon_url = app_data.get("icon", "")
    banner_url = app_data.get("graphic", "")

    if icon_url:
        download_image(icon_url, os.path.join(game_dir, "icon.png"))
    if banner_url:
        download_image(banner_url, os.path.join(game_dir, "banner.png"))

    screenshot_links: List[str] = []
    screenshots_data = app_data.get("media", {}).get("screenshots", [])
    for idx, shot in enumerate(screenshots_data[:20], 1):
        shot_url = shot.get("url")
        if not shot_url:
            continue

        ext = normalize_ext(shot_url)
        local_name = f"{idx}.{ext}"
        local_path = os.path.join(screenshots_dir, local_name)
        if download_image(shot_url, local_path):
            screenshot_links.append(f"{CDN_BASE_URL}/{game_id}/screenshots/{local_name}")

    return {
        "id": game_id,
        "title": title,
        "package": package,
        "details": {
            "downloads": format_downloads(raw_downloads),
            "rating": rating,
            "size": format_size(size_bytes),
            "ageRating": age,
            "androidVersion": android_v,
            "version": version,
        },
        "description": (desc or "").strip(),
        "whatsNew": (whats_new or "").strip(),
        "media": {
            "iconUrl": f"{CDN_BASE_URL}/{game_id}/icon.png",
            "bannerUrl": f"{CDN_BASE_URL}/{game_id}/banner.png",
            "screenshots": screenshot_links,
        },
        "downloadLinks": {
            "playStoreUrl": f"https://play.google.com/store/apps/details?id={package}" if package else None,
            "galaxyStoreUrl": f"https://galaxystore.samsung.com/detail/{package}" if package else None,
            "mirrors": ["https://dummy-mirror1.com"],
            "apk1": None,
            "apk2": None,
        },
    }


def load_games() -> dict:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_games(data: dict) -> None:
    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def upsert_popular_games() -> None:
    data = load_games()
    games: List[dict] = data.get("games", [])

    by_id: Dict[str, dict] = {g.get("id"): g for g in games if g.get("id")}

    prepared: Dict[str, dict] = {}

    for target_id, unames in POPULAR_TARGETS:
        print(f"[target] {target_id}")

        # Try fetching fresh data; fallback to existing entry if fetch fails.
        new_entry = None
        for uname in unames:
            app_data = get_game_details(uname)
            if app_data and app_data.get("package"):
                print(f"  - found source: {uname}")
                new_entry = build_game_info(target_id, app_data)
                break

        if new_entry is None:
            if target_id in by_id:
                print(f"  - source unavailable, keeping existing: {target_id}")
                new_entry = by_id[target_id]
            else:
                print(f"  - source unavailable, skipped: {target_id}")
                continue

        # Keep downloadLinks format stable.
        dl = new_entry.get("downloadLinks", {})
        if isinstance(dl, dict):
            dl["mirrors"] = ["https://dummy-mirror1.com"]
            dl.setdefault("apk1", None)
            dl.setdefault("apk2", None)

        prepared[target_id] = new_entry
        time.sleep(0.2)

    # Build final order: requested popular first, remaining old ones after.
    popular_order = [item[0] for item in POPULAR_TARGETS if item[0] in prepared]
    remaining = [g for g in games if g.get("id") not in set(popular_order)]
    data["games"] = [prepared[i] for i in popular_order] + remaining

    save_games(data)
    print(f"done: total_games={len(data['games'])}, popular_on_top={popular_order}")


if __name__ == "__main__":
    if not os.path.exists("games"):
        os.makedirs("games")
    upsert_popular_games()
