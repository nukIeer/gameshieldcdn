"""PC (Winlator) oyunlarını ve GitHub'dan resmi APK'sı yayınlanan açık kaynak oyunları ekler.

PC oyunları için şema:
    "platform": "windows"           -> uygulama "PC · Winlator gerekli" rozeti gösterir
    "requires": ["winlator"]        -> önce bu id'li kayıt (Winlator) kurulmalı
    downloadLinks.pcStoreUrls       -> ücretli oyunlar için resmi mağaza linkleri (dosya yok)
    downloadLinks.load1             -> sadece yasal olarak ücretsiz dağıtılan oyunlarda dosya linki
"""
import json
import os
import re
from typing import List, Optional

import requests
from PIL import Image

from add_playstore_games import CDN_BASE_URL, GAMES_JSON_PATH, WEBPAGE_URL, build_play_entry, save_media
from update_apks import fetch_github_apk

STEAM_ART = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/{name}"

WINLATOR_STEPS = (
    "\n\nHow to play on Android:\n"
    "1. Install Winlator (listed in this market).\n"
    "2. {step2}\n"
    "3. In Winlator, create a container, open the game folder from the file manager and run the .exe."
)


def steam_details(appid: int) -> dict:
    res = requests.get(f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english", timeout=20)
    return res.json()[str(appid)]["data"]


def pc_entry(game_id: str, title: str, description: str, media: dict, version: str, is_free: bool,
             pegi: str, load1: Optional[str], store_urls: List[str], webpage: str, apk_info: Optional[dict] = None) -> dict:
    dl = {
        "playStoreUrl": None,
        "galaxyStoreUrl": None,
        "pcStoreUrls": store_urls,
        "webpage": [webpage],
        "load1": load1,
        "load2": None,
    }
    if apk_info:
        dl["apkInfo"] = apk_info
    return {
        "id": game_id,
        "title": title,
        "package": None,
        "platform": "windows",
        "requires": ["winlator"],
        "details": {
            "downloads": "N/A",
            "rating": 0,
            "size": (apk_info or {}).get("size", "N/A"),
            "ageRating": pegi,
            "androidVersion": "N/A",
            "version": version,
            "isFree": is_free,
        },
        "description": description,
        "whatsNew": "",
        "media": media,
        "downloadLinks": dl,
    }


def steam_media(game_id: str, appid: int) -> dict:
    data = steam_details(appid)
    return save_media(
        game_id,
        STEAM_ART.format(appid=appid, name="library_600x900.jpg"),
        STEAM_ART.format(appid=appid, name="library_hero.jpg"),
        [s["path_full"] for s in data.get("screenshots", [])],
    )


def build_gta5() -> dict:
    return pc_entry(
        "gta5",
        "Grand Theft Auto V (PC)",
        "Explore Los Santos and Blaine County in Rockstar's open-world classic. This is the PC version and "
        "runs on Android through Winlator. The game is NOT included: you must buy it on Steam, Epic Games "
        "or the Rockstar Store and download it with your own account."
        + WINLATOR_STEPS.format(step2="Buy the game and copy the installed game folder to your phone.")
        + "\n\nPerformance: GTA V is a heavy game. It only runs on high-end phones (Snapdragon 8 Gen 2 or "
        "newer recommended) at low settings. The \"Legacy\" edition that comes with your purchase uses "
        "DirectX 11 and works better in Winlator than the \"Enhanced\" edition. GTA Online does not work "
        "because of its anti-cheat.",
        steam_media("gta5", 3240220),
        "Enhanced / Legacy",
        False,
        "PEGI-18",
        None,
        [
            "https://store.steampowered.com/app/3240220/",
            "https://store.epicgames.com/p/grand-theft-auto-v",
            "https://store.rockstargames.com/game/buy-gta-v",
        ],
        "https://store.steampowered.com/app/3240220/",
    )


def build_teeworlds() -> dict:
    gh = fetch_github_apk("teeworlds/teeworlds", r"win64\.zip$")
    return pc_entry(
        "teeworlds",
        "Teeworlds (PC)",
        "A free, open-source online multiplayer shooter with cute 2D characters. Grapple across maps, "
        "play deathmatch or capture the flag with players around the world."
        + WINLATOR_STEPS.format(step2="Download the Windows zip below and extract it on your phone."),
        steam_media("teeworlds", 380840),
        gh["info"]["version"],
        True,
        "PEGI-7",
        gh["path"],
        ["https://store.steampowered.com/app/380840/"],
        "https://teeworlds.com/",
        gh["info"],
    )


def build_spelunky() -> dict:
    media = save_media(
        "spelunkyclassic",
        "https://spelunkyworld.com/images/goldidol.gif",
        "https://spelunkyworld.com/images/spelunky-pc-screen.png",
        ["https://spelunkyworld.com/images/spelunky-pc-screen.png"],
    )
    # İkon 32x32 piksel sanatı; bulanıklaşmasın diye keskin büyütülür.
    icon_path = os.path.join("games", "spelunkyclassic", "icon.png")
    idol = Image.open(requests.get("https://spelunkyworld.com/images/goldidol.gif", stream=True, timeout=20).raw)
    idol.convert("RGBA").resize((512, 512), Image.NEAREST).save(icon_path, "PNG", optimize=True)
    return pc_entry(
        "spelunkyclassic",
        "Spelunky Classic (PC)",
        "The original 2008 freeware Spelunky by Derek Yu. Explore randomly generated caves, grab treasure, "
        "rescue damsels and avoid deadly traps. Released for free by its creator."
        + WINLATOR_STEPS.format(step2="Download the zip below and extract it on your phone."),
        media,
        "1.1",
        True,
        "PEGI-7",
        "https://www.derekyu.com/games/spelunky_1_1.zip",
        [],
        "https://spelunkyworld.com/original.html",
    )


def build_github_android(game_id: str, package: str, repo: str, pattern: str) -> Optional[dict]:
    entry = build_play_entry(game_id, package)
    gh = fetch_github_apk(repo, pattern)
    if not entry or not gh:
        return None
    entry["downloadLinks"]["load1"] = gh["path"]
    entry["downloadLinks"]["apkInfo"] = gh["info"]
    entry["details"]["size"] = gh["info"]["size"]
    return entry


def build_osu() -> Optional[dict]:
    gh = fetch_github_apk("ppy/osu", r"\.apk$")
    media = save_media(
        "osu",
        "https://raw.githubusercontent.com/ppy/osu/master/assets/lazer.png",
        None,
        [],
    )
    if not gh or not media:
        return None
    return {
        "id": "osu",
        "title": "osu!",
        "package": "sh.ppy.osulazer",
        "details": {
            "downloads": "N/A",
            "rating": 0,
            "size": gh["info"]["size"],
            "ageRating": "PEGI-3",
            "androidVersion": "N/A",
            "version": gh["info"]["version"],
            "isFree": True,
        },
        "description": "The official open-source rhythm game osu! (lazer). Click circles, follow sliders and "
        "spin to the beat of thousands of community-made beatmaps. Android builds are published by the "
        "osu! team on GitHub.",
        "whatsNew": "",
        "media": media,
        "downloadLinks": {
            "playStoreUrl": None,
            "galaxyStoreUrl": None,
            "webpage": ["https://osu.ppy.sh/"],
            "load1": gh["path"],
            "load2": None,
            "apkInfo": gh["info"],
        },
    }


def main() -> None:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data["games"]
    ids = {g["id"] for g in games}

    builders = {
        "gta5": build_gta5,
        "teeworlds": build_teeworlds,
        "spelunkyclassic": build_spelunky,
        "shatteredpd": lambda: build_github_android(
            "shatteredpd", "com.shatteredpixel.shatteredpixeldungeon",
            "00-Evan/shattered-pixel-dungeon", r"-Android\.apk$"),
        "osu": build_osu,
    }
    for game_id, build in builders.items():
        if game_id in ids:
            continue
        print(f"+ {game_id}")
        entry = build()
        if entry:
            entry["title"] = re.sub(r"\s+", " ", entry["title"]).strip()
            games.append(entry)

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print(f"toplam: {len(games)}")


if __name__ == "__main__":
    main()
