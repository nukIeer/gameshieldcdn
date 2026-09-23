"""Winlator APK'sı içinde çalışan oyunları ve GitHub'dan resmi APK'sı yayınlanan açık kaynak oyunları ekler.

Şema:
    "requires": ["winlator"]        -> Winlator APK'sı içinde çalışır; uygulama "Winlator gerekli"
                                       rozeti gösterir ve önce bu id'li kaydı (Winlator) kurdurur
    downloadLinks.pcStoreUrls       -> ücretli oyunlar için resmi mağaza linkleri (dosya yok)
    downloadLinks.load1             -> oyun dosyası (ücretsizse) ya da resmi mağaza sayfası (ücretliyse)
    downloadLinks.load2             -> Winlator APK'sı (update_apks.py her gün senkronlar)
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
        "webpage": [WEBPAGE_URL.format(id=game_id)],
        "load1": load1,
        "load2": None,
    }
    if apk_info:
        dl["apkInfo"] = apk_info
    return {
        "id": game_id,
        "title": title,
        "package": None,
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
    shots = [s["path_full"] for s in data.get("screenshots", [])]
    # Eski oyunlarda dikey kapak/hero görseli olmayabiliyor; mağaza başlık görseline düş.
    for icon, banner in (("library_600x900.jpg", "library_hero.jpg"), ("header.jpg", "header.jpg")):
        media = save_media(game_id, STEAM_ART.format(appid=appid, name=icon),
                           STEAM_ART.format(appid=appid, name=banner), shots)
        if media:
            return media
    return None


def build_gta5() -> dict:
    return pc_entry(
        "gta5",
        "Grand Theft Auto V",
        "Explore Los Santos and Blaine County in Rockstar's open-world classic. It runs on your phone inside the "
        "Winlator app. The game is NOT included: you must buy it on Steam, Epic Games "
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
        "https://store.steampowered.com/app/3240220/",
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
        "Teeworlds",
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
        "Spelunky Classic",
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
            "webpage": [WEBPAGE_URL.format(id="osu")],
            "load1": gh["path"],
            "load2": None,
            "apkInfo": gh["info"],
        },
    }


# Winlator'da çalıştığı raporlanan ücretli PC oyunları: sadece resmi mağaza linkleri, dosya yok.
# (id, steam appid, gog slug ya da None, seviye, GPU, performans notu)
# Seviye: low = orta sınıf telefon da yeter, mid = Snapdragon 8 Gen 2+, high = Snapdragon 8 Elite + 12GB RAM
WINLATOR_STORE_GAMES = [
    ("halflife", 70, None, "low", "adreno", "Stable, light on resources"),
    ("cod2", 2630, None, "low", "adreno", "Smooth even on budget phones"),
    ("cod4", 7940, None, "low", "adreno", "Smooth on mid-range phones"),
    ("cuphead", 268910, "cuphead", "low", "adreno", "Runs excellently, 60 FPS on Snapdragon 8 Gen 3"),
    ("popsandsoftime", 13600, "prince_of_persia_the_sands_of_time", "low", "both", "Smooth, also on Mali GPUs"),
    ("dmc4", 329050, None, "low", "both", "Smooth combat, also on Mali GPUs"),
    ("aoe2", 813780, None, "mid", "adreno", "Works well with touch controls"),
    ("fallout3", 22370, "fallout_3_game_of_the_year_edition", "mid", "adreno", "30-40 FPS at 800x600"),
    ("falloutnv", 22380, "fallout_new_vegas_ultimate_edition", "mid", "adreno", "Good performance on newer phones"),
    ("oblivion", 22330, None, "mid", "adreno", "Playable with the right settings"),
    ("skyrim", 489830, None, "mid", "adreno", "Stable gameplay"),
    ("deadspace", 17470, "dead_space", "mid", "adreno", "Solid performance"),
    ("deadspace2", 47780, None, "mid", "adreno", "Solid performance"),
    ("acbrotherhood", 48190, None, "mid", "adreno", "Smooth, best with a controller"),
    ("acrevelations", 201870, None, "mid", "adreno", "Smooth, best with a controller"),
    ("ac3", 208480, None, "mid", "adreno", "Smooth, best with a controller"),
    ("acrogue", 311560, None, "mid", "adreno", "Smooth, best with a controller"),
    ("re5", 21690, None, "mid", "both", "30+ FPS, also on Mali GPUs"),
    ("burnoutparadise", 1238080, None, "mid", "adreno", "Runs very well"),
    ("hades", 1145360, None, "mid", "adreno", "Consistent performance"),
    ("ets2", 227300, None, "mid", "adreno", "Relaxing, runs well"),
    ("witcher3", 292030, "the_witcher_3_wild_hunt_game_of_the_year_edition", "high", "adreno", "Playable at 720p on Snapdragon 8 Elite"),
]

TIER_CHIPS = {
    "low": "Snapdragon 7 series / 8 Gen 1 or better, 6-8GB RAM",
    "mid": "Snapdragon 8 Gen 2 or better, 8-12GB RAM",
    "high": "Snapdragon 8 Elite, 12-16GB RAM",
}


def winlator_info(tier: str, gpu: str, note: str) -> dict:
    """Uygulama/site bu kartı "Hangi telefonda çalışır?" bölümü olarak gösterir."""
    return {
        "tier": tier,
        "minDevice": TIER_CHIPS[tier],
        "gpu": ["adreno", "mali"] if gpu == "both" else [gpu],
        "performance": note,
        "settings": "Turnip + DXVK (Mali: VirGL), 960x544, Box64 preset: Performance",
    }


def build_winlator_store_game(game_id: str, appid: int, gog: Optional[str], tier: str, gpu: str, note: str) -> dict:
    data = steam_details(appid)
    steam_url = f"https://store.steampowered.com/app/{appid}/"
    gog_url = f"https://www.gog.com/en/game/{gog}" if gog else None
    storage = re.search(r"Storage:</strong>\s*([\d.]+)\s*GB", (data.get("pc_requirements") or {}).get("minimum", "") or "")
    pegi = ((data.get("ratings") or {}).get("pegi") or {}).get("rating")
    where = "GOG (DRM-free, works best in Winlator) or Steam" if gog else "Steam"

    entry = pc_entry(
        game_id,
        data["name"],
        (data.get("short_description") or "").strip()
        + WINLATOR_STEPS.format(step2=f"Buy the game on {where} and copy the installed game folder to your phone.")
        + f"\n\nPhone needed: {TIER_CHIPS[tier]}. {note}.",
        steam_media(game_id, appid),
        "Latest",
        False,
        f"PEGI-{pegi}" if pegi else "N/A",
        gog_url or steam_url,
        [u for u in (gog_url, steam_url) if u],
        steam_url,
    )
    entry["details"]["size"] = f"{storage.group(1)}GB" if storage else "N/A"
    entry["winlator"] = winlator_info(tier, gpu, note)
    return entry


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
    for args in WINLATOR_STORE_GAMES:
        builders[args[0]] = lambda a=args: build_winlator_store_game(*a)

    for game_id, build in builders.items():
        if game_id in ids:
            continue
        print(f"+ {game_id}")
        entry = build()
        if entry:
            entry["title"] = re.sub(r"\s+", " ", re.sub(r"[™®]", "", entry["title"])).strip()
            games.append(entry)

    # Önceden eklenmiş Winlator oyunlarının "hangi telefonda çalışır" kartı.
    existing_info = {
        "gta5": winlator_info("high", "adreno", "45-60 FPS at 960x544 on Snapdragon 8 Elite"),
        "teeworlds": winlator_info("low", "both", "Very light, runs on most phones"),
        "spelunkyclassic": winlator_info("low", "both", "Very light, runs on most phones"),
    }
    for g in games:
        if g["id"] in existing_info and "winlator" not in g:
            g["winlator"] = existing_info[g["id"]]

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print(f"toplam: {len(games)}")


if __name__ == "__main__":
    main()
