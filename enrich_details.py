"""games.json'daki eksik (N/A / 0) detayları gerçek kaynaklardan doldurur.

`--refresh` ile (haftalık workflow) eksik olmasa da puan, indirme, sürüm, yaş sınırı ve
"Yenilikler" metnini günceller; Play Store'dan kaldırılan oyunları da işaretler.

- rating / downloads / ageRating: Google Play; Steam oyunlarında Steam kullanıcı yorumları
- size / androidVersion: Aptoide (sahte kayıtlar hariç); GitHub'dan gelenlerde release dosyası
- downloads (GitHub): tüm sürümlerin toplam indirme sayısı
Veri bulunamayan alanlar uydurulmaz.
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests

from add_playstore_games import AGE_RE, format_installs, play_lookup
from update_apks import FAKE_VERSIONS, GAMES_JSON_PATH, fetch_meta

MISSING = (None, "", "N/A", 0, 0.0)
MIN_APTOIDE_VOTES = 50
VARIES = "Varies with device"

SDK_TO_ANDROID = {
    9: "2.3", 10: "2.3.3", 14: "4.0", 15: "4.0.3", 16: "4.1", 17: "4.2", 18: "4.3", 19: "4.4",
    21: "5.0", 22: "5.1", 23: "6.0", 24: "7.0", 25: "7.1", 26: "8.0", 27: "8.1", 28: "9",
    29: "10", 30: "11", 31: "12", 32: "12L", 33: "13", 34: "14", 35: "15", 36: "16",
}


def steam_rating(appid: str) -> Optional[float]:
    res = requests.get(
        f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all&purchase_type=all&num_per_page=0",
        timeout=20,
    )
    s = res.json().get("query_summary") or {}
    total = s.get("total_reviews") or 0
    if total < MIN_APTOIDE_VOTES:
        return None
    return round(5 * s["total_positive"] / total, 2)


def github_downloads(repo: str, pattern: str) -> int:
    total, page = 0, 1
    while True:
        res = requests.get(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}", timeout=20)
        releases = res.json() if res.status_code == 200 else []
        if not releases:
            return total
        for rel in releases:
            total += sum(a.get("download_count", 0) for a in rel.get("assets", [])
                         if re.search(pattern, a.get("name", "")))
        page += 1


def collect(game: dict) -> dict:
    """Ağ isteklerini yapar; games.json'a dokunmaz."""
    out = {}
    pkg = game.get("package")
    dl = game.get("downloadLinks") or {}
    info = dl.get("apkInfo") or {}

    if pkg:
        out["play"] = play_lookup(pkg)
        out["aptoide"] = fetch_meta(pkg)
    if info.get("source") == "github":
        out["gh_downloads"] = github_downloads(info["repo"], info.get("assetPattern") or r"\.apk$")
    for url in dl.get("pcStoreUrls") or []:
        m = re.search(r"store\.steampowered\.com/app/(\d+)", url)
        if m:
            out["steam_rating"] = steam_rating(m.group(1))
            break
    return out


def apply(game: dict, data: dict, refresh: bool = False) -> None:
    d = game.setdefault("details", {})
    play = data.get("play")

    def stale(key: str) -> bool:
        return refresh or d.get(key) in MISSING
    meta = data.get("aptoide") or {}
    f = meta.get("file") or {}
    # Aptoide'deki "999.0" sürümlü sahte kopyaların verisi kullanılmaz.
    aptoide_ok = bool(f) and str(f.get("vername")) not in FAKE_VERSIONS

    if stale("rating"):
        if play and play.get("score"):
            d["rating"] = round(play["score"], 2)
        elif data.get("steam_rating"):
            d["rating"] = data["steam_rating"]
        elif aptoide_ok:
            pr = (meta.get("stats") or {}).get("prating") or {}
            if (pr.get("total") or 0) >= MIN_APTOIDE_VOTES:
                d["rating"] = round(pr["avg"], 2)

    if stale("downloads"):
        if play and play.get("realInstalls"):
            d["downloads"] = format_installs(play["realInstalls"])
        elif data.get("gh_downloads"):
            d["downloads"] = format_installs(data["gh_downloads"])

    if stale("ageRating") and play:
        age = AGE_RE.search(play.get("contentRating") or "")
        if age:
            d["ageRating"] = f"PEGI-{age.group(1)}"

    if refresh and play:
        # Play çoğu oyunda sürümü "Varies with device" diye veriyor; o durumda mevcut sürüm kalır.
        version = play.get("version")
        if version and version != VARIES:
            d["version"] = version
        if play.get("recentChanges"):
            game["whatsNew"] = play["recentChanges"].strip()

    apk_size = ((game.get("downloadLinks") or {}).get("apkInfo") or {}).get("size")
    if d.get("size") in MISSING:
        if apk_size:
            d["size"] = apk_size
        elif aptoide_ok and f.get("filesize"):
            d["size"] = f"{round(f['filesize'] / (1024 * 1024), 1)}MB"

    if d.get("androidVersion") in MISSING and aptoide_ok:
        sdk = (f.get("hardware") or {}).get("sdk")
        if sdk in SDK_TO_ANDROID:
            d["androidVersion"] = f"{SDK_TO_ANDROID[sdk]}+"


def mark_delisted(game: dict, data: dict) -> bool:
    """Play Store'dan kaldırılan oyunun ölü linklerini siler, "nostalgia" etiketi ekler."""
    dl = game.get("downloadLinks") or {}
    if not game.get("package") or not dl.get("playStoreUrl") or data.get("play"):
        return False
    dl["playStoreUrl"] = None
    dl["galaxyStoreUrl"] = None
    tags = game.setdefault("tags", [])
    if "nostalgia" not in tags:
        tags.append("nostalgia")
    return True


def main() -> None:
    refresh = "--refresh" in sys.argv
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data["games"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(collect, games))
    for game, res in zip(games, results):
        apply(game, res, refresh)
        if refresh and mark_delisted(game, res):
            print(f"Play Store'dan kalkmis: {game['id']}")

    # Winlator ile çalışan oyunlar Winlator'ın Android sürüm şartını devralır.
    winlator = next((g for g in games if g["id"] == "winlator"), None)
    for game in games:
        d = game["details"]
        if winlator and "winlator" in (game.get("requires") or []):
            d["androidVersion"] = winlator["details"].get("androidVersion", VARIES)
        # Play Store artık min. Android sürümünü ve boyutu göstermiyor; kendisi de "cihaza göre değişir" diyor.
        for key in ("size", "androidVersion"):
            if d.get(key) in MISSING:
                d[key] = VARIES

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")

    for key in ("rating", "downloads", "size", "androidVersion"):
        left = [g["id"] for g in games if g["details"].get(key) in MISSING]
        print(f"{key}: eksik {len(left)} {left if len(left) < 10 else ''}")


if __name__ == "__main__":
    main()
