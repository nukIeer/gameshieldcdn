import io
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import requests
from google_play_scraper import app as play_app
from google_play_scraper.exceptions import NotFoundError
from PIL import Image, ImageFilter

from update_apks import fetch_meta, pick_trusted_apk

CDN_BASE_URL = "https://cdn.jsdelivr.net/gh/nukIeer/gameshieldcdn@master/games"
WEBPAGE_URL = "https://game-guard-three.vercel.app/"
GAMES_JSON_PATH = "games.json"
MAX_SCREENSHOTS = 8

# (id, Play Store paket adı)
TARGETS: List[Tuple[str, str]] = [
    # GTA (ücretli olanlar sadece Play Store linkiyle)
    ("gtasanandreas", "com.rockstargames.gtasa"),
    ("gtavicecity", "com.rockstargames.gtavc"),
    ("gta3", "com.rockstar.gta3"),
    ("gtalibertycity", "com.rockstargames.gtalcs"),
    ("gtachinatown", "com.rockstargames.gtactw"),
    # Supercell
    ("clashofclans", "com.supercell.clashofclans"),
    ("clashroyale", "com.supercell.clashroyale"),
    ("hayday", "com.supercell.hayday"),
    ("boombeach", "com.supercell.boombeach"),
    ("squadbusters", "com.supercell.squad"),
    # Aksiyon / FPS / MOBA
    ("codmobile", "com.activision.callofduty.shooter"),
    ("mobilelegends", "com.mobile.legends"),
    ("standoff2", "com.axlebolt.standoff2"),
    ("genshin", "com.miHoYo.GenshinImpact"),
    ("starrail", "com.HoYoverse.hkrpgoversea"),
    ("honorofkings", "com.levelinfinite.sgameGlobal"),
    ("shadowfight2", "com.nekki.shadowfight"),
    ("shadowfight3", "com.nekki.shadowfight3"),
    ("deadtrigger", "com.madfingergames.deadtrigger"),
    ("deadtrigger2", "com.madfingergames.deadtrigger2"),
    ("pubglite", "com.tencent.iglite"),
    ("minecraftpe", "com.mojang.minecraftpe"),
    ("moderncombat5", "com.gameloft.android.ANMP.GloftM5HM"),
    ("gangstarvegas", "com.gameloft.android.ANMP.GloftGGHM"),
    ("gangstarneworleans", "com.gameloft.android.ANMP.GloftOLHM"),
    ("pixelgun3d", "com.pixel.gun3d"),
    ("minimilitia", "com.appsomniacs.da2"),
    ("sniper3d", "com.fungames.sniper3d"),
    # Yarış
    ("asphalt", "com.gameloft.android.ANMP.GloftA9HM"),
    ("asphalt8", "com.gameloft.android.ANMP.GloftA8HM"),
    ("hillclimb2", "com.fingersoft.hcr2"),
    ("carparking", "com.olzhas.carparking.multyplayer"),
    ("csr2", "com.naturalmotion.customstreetracer2"),
    ("nfsnolimits", "com.ea.game.nfs14_row"),
    ("trafficracer", "com.skgames.trafficracer"),
    ("bikerace", "com.topfreegames.bikeracefreeworld"),
    ("crashofcars", "com.notdoppler.crashofcars"),
    # Nostalji / klasik casual
    ("subwaysurfers", "com.kiloo.subwaysurf"),
    ("templerun2", "com.imangi.templerun2"),
    ("talkingtomcat", "com.outfit7.talkingtom"),
    ("talkingtomcat2", "com.outfit7.talkingtom2free"),
    ("talkingangela", "com.outfit7.talkingangelafree"),
    ("mytalkingtom", "com.outfit7.mytalkingtomfree"),
    ("talkingben", "com.outfit7.talkingben"),
    ("talkingginger", "com.outfit7.talkinggingerfree"),
    ("talkingpierre", "com.outfit7.talkingpierrefree"),
    ("jetpackjoyride", "com.halfbrick.jetpackjoyride"),
    ("fruitninja", "com.halfbrick.fruitninjafree"),
    ("fruitninja2", "com.halfbrick.fruitninjax"),
    ("minionrush", "com.gameloft.android.ANMP.GloftDMHM"),
    ("doodlejump", "com.lima.doodlejump"),
    ("crossyroad", "com.yodo1.crossyroad"),
    ("hungryshark", "com.fgol.HungrySharkEvolution"),
    ("angrybirds2", "com.rovio.baba"),
    ("angrybirdstransformers", "com.rovio.angrybirdstransformers"),
    ("badpiggies", "com.rovio.BadPiggies"),
    ("cuttherope", "com.zeptolab.ctr.ads"),
    ("cuttherope2", "com.zeptolab.ctr2.f2p.google"),
    ("pvz", "com.ea.game.pvzfree_row"),
    ("pvz2", "com.ea.game.pvz2_row"),
    ("smashhit", "com.mediocre.smashhit"),
    ("headsoccer", "com.dnddream.headsoccer.android"),
    ("clumsyninja", "com.naturalmotion.clumsyninja"),
    ("badland", "com.frogmind.badland"),
    ("zigzag", "com.ketchapp.zigzaggame"),
    ("ketchappstack", "com.ketchapp.stack"),
    ("paperio2", "io.voodoo.paper2"),
    ("helixjump", "com.h8games.helixjump"),
    ("bomberfriends", "com.hyperkani.bomberfriends"),
    ("plagueinc", "com.miniclip.plagueinc"),
    ("candycrush", "com.king.candycrushsaga"),
    ("candycrushsoda", "com.king.candycrushsodasaga"),
    ("farmheroes", "com.king.farmheroessaga"),
    ("homescapes", "com.playrix.homescapes"),
    ("gardenscapes", "com.playrix.gardenscapes"),
    ("township", "com.playrix.township"),
    ("cookingfever", "com.nordcurrent.canteenhd"),
    ("criminalcase", "com.prettysimple.criminalcaseandroid"),
    ("simsfreeplay", "com.ea.games.simsfreeplay_row"),
    ("simcity", "com.ea.game.simcitymobile_row"),
    ("dragonmania", "com.gameloft.android.ANMP.GloftDOHM"),
    ("agario", "com.miniclip.agar.io"),
    ("pokemongo", "com.nianticlabs.pokemongo"),
    ("coinmaster", "com.moonactive.coinmaster"),
    ("chess", "com.chess"),
    ("uno", "com.matteljv.uno"),
    # Strateji
    ("lordsmobile", "com.igg.android.lordsmobile"),
    ("riseofkingdoms", "com.lilithgame.roc.gp"),
    ("raidshadowlegends", "com.plarium.raidlegends"),
]

# Play Store'dan kalkmış, çevrimdışı oynanabilen klasikler. Aptoide'den sadece orijinal
# geliştirici imzalı APK kabul edilir; açıklamalar yükleyicinin metnine güvenmemek için elle yazıldı.
DELISTED: Dict[str, Tuple[str, str, str]] = {
    "flappybird": (
        "com.dotgears.flappybird",
        "Flappy Bird",
        "The original 2014 Flappy Bird by Dong Nguyen (.GEARS Studios). Tap to flap and guide the bird "
        "through the gaps between the pipes. The game was removed from Google Play by its creator in "
        "February 2014 at the height of its popularity.",
    ),
    "deerhunterclassic": (
        "com.glu.deerhunt2",
        "Deer Hunter Classic",
        "Glu Mobile's hunting game from 2013. Travel across hunting regions, track animals and take the "
        "perfect shot with a large collection of rifles and scopes. It is no longer on Google Play.",
    ),
    "vector2": (
        "com.nekki.vector2",
        "Vector 2",
        "The parkour sequel by Nekki. Run, jump and slide through a futuristic lab while escaping the "
        "hunters. It is no longer on Google Play.",
    ),
}

AGE_RE = re.compile(r"PEGI\s*(\d+)")


def format_installs(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n // 1_000_000_000}B+"
    if n >= 1_000_000:
        return f"{n // 1_000_000}M+"
    if n >= 1_000:
        return f"{n // 1_000}K+"
    return str(n) if n else "N/A"


def fetch_image(url: Optional[str]) -> Optional[Image.Image]:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"  ! gorsel indirilemedi: {e}")
        return None


def banner_from_icon(icon: Image.Image) -> Image.Image:
    """Banner'ı olmayan oyunlar için ikondan bulanık arka planlı 1024x500 banner üretir."""
    bg = icon.resize((1024, 1024)).crop((0, 262, 1024, 762)).filter(ImageFilter.GaussianBlur(40))
    fg = icon.resize((360, 360), Image.LANCZOS)
    bg.paste(fg, ((1024 - 360) // 2, (500 - 360) // 2))
    return bg


def save_media(game_id: str, icon_url: str, banner_url: Optional[str], shot_urls: List[str]) -> Optional[dict]:
    game_dir = os.path.join("games", game_id)
    shots_dir = os.path.join(game_dir, "screenshots")

    icon = fetch_image(icon_url)
    if not icon:
        return None
    banner = fetch_image(banner_url) or banner_from_icon(icon)

    os.makedirs(shots_dir, exist_ok=True)
    icon.resize((512, 512), Image.LANCZOS).save(os.path.join(game_dir, "icon.png"), "PNG", optimize=True)
    banner.resize((1024, 500), Image.LANCZOS).save(os.path.join(game_dir, "banner.png"), "PNG", optimize=True)

    shots = []
    for url in shot_urls[:MAX_SCREENSHOTS]:
        img = fetch_image(url)
        if img:
            name = f"{len(shots) + 1}.jpg"
            img.save(os.path.join(shots_dir, name), "JPEG", quality=85)
            shots.append(f"{CDN_BASE_URL}/{game_id}/screenshots/{name}")

    return {
        "iconUrl": f"{CDN_BASE_URL}/{game_id}/icon.png",
        "bannerUrl": f"{CDN_BASE_URL}/{game_id}/banner.png",
        "screenshots": shots,
    }


def play_lookup(package: str) -> Optional[dict]:
    # Bazı oyunlar bölgeye göre gizli; kalkmış saymadan önce ABD'yi de dene.
    for country in ("tr", "us"):
        try:
            return play_app(package, lang="en", country=country)
        except NotFoundError:
            continue
    return None


def build_play_entry(game_id: str, package: str) -> Optional[dict]:
    a = play_lookup(package)
    if not a:
        print(f"  ! Play Store'da yok: {package}")
        return None

    media = save_media(
        game_id,
        f"{a.get('icon')}=s512",
        f"{a.get('headerImage')}=w1024-h500" if a.get("headerImage") else None,
        [f"{u}=w720" for u in a.get("screenshots") or []],
    )
    if not media:
        return None

    age = AGE_RE.search(a.get("contentRating") or "")
    return {
        "id": game_id,
        "title": re.sub(r"\s+", " ", a.get("title") or game_id).strip(),
        "package": package,
        "details": {
            "downloads": format_installs(int(re.sub(r"[^0-9]", "", a.get("installs") or "") or 0)),
            "rating": round(a.get("score") or 0, 2),
            "size": "N/A",
            "ageRating": f"PEGI-{age.group(1)}" if age else "N/A",
            "androidVersion": "N/A",
            "version": a.get("version") or "N/A",
            "isFree": bool(a.get("free")),
        },
        "description": (a.get("description") or "").strip(),
        "whatsNew": (a.get("recentChanges") or "").strip(),
        "media": media,
        "downloadLinks": {
            "playStoreUrl": f"https://play.google.com/store/apps/details?id={package}",
            "galaxyStoreUrl": f"https://galaxystore.samsung.com/detail/{package}",
            "webpage": [WEBPAGE_URL],
            "load1": None,
            "load2": None,
        },
    }


def build_delisted_entry(game_id: str, package: str, title: str, description: str) -> Optional[dict]:
    meta = fetch_meta(package)
    apk = pick_trusted_apk(meta, None)
    if not apk:
        print(f"  ! guvenilir APK yok: {package}")
        return None

    media = save_media(
        game_id,
        meta.get("icon"),
        meta.get("graphic"),
        [s.get("url") for s in (meta.get("media") or {}).get("screenshots") or [] if s.get("url")],
    )
    if not media:
        return None

    stats = meta.get("stats") or {}
    return {
        "id": game_id,
        "title": title,
        "package": package,
        "tags": ["nostalgia"],
        "details": {
            "downloads": format_installs(stats.get("pdownloads") or 0),
            "rating": round((stats.get("prating") or {}).get("avg") or 0, 2),
            "size": apk["info"]["size"],
            "ageRating": (meta.get("age") or {}).get("pegi") or "N/A",
            "androidVersion": "N/A",
            "version": apk["info"]["version"],
            "isFree": True,
        },
        "description": description,
        "whatsNew": "",
        "media": media,
        "downloadLinks": {
            "playStoreUrl": None,
            "galaxyStoreUrl": None,
            "webpage": [WEBPAGE_URL],
            "load1": None,
            "load2": None,
        },
    }


def mark_delisted(games: List[dict]) -> None:
    """Play Store'dan kalkmış oyunların ölü Play/Galaxy linklerini kaldırır."""
    for g in games:
        dl = g.get("downloadLinks") or {}
        if not dl.get("playStoreUrl"):
            continue
        if play_lookup(g["package"]) is None:
            print(f"- Play Store'dan kalkmis: {g['id']} ({g['package']})")
            dl["playStoreUrl"] = None
            dl["galaxyStoreUrl"] = None
            tags = g.setdefault("tags", [])
            if "nostalgia" not in tags:
                tags.append("nostalgia")


def main() -> None:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data["games"]
    ids = {g["id"] for g in games} | set(os.listdir("games"))
    packages = {g["package"] for g in games}

    jobs = [(i, p, None) for i, p in TARGETS] + [(i, v[0], v) for i, v in DELISTED.items()]
    added = 0
    for game_id, package, delisted in jobs:
        if package in packages or game_id in ids:
            continue
        print(f"+ {game_id} ({package})")
        entry = build_delisted_entry(game_id, *delisted) if delisted else build_play_entry(game_id, package)
        if entry:
            games.append(entry)
            packages.add(package)
            ids.add(game_id)
            added += 1

    mark_delisted(games)

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print(f"Eklenen oyun: {added}, toplam: {len(games)}")


if __name__ == "__main__":
    main()
