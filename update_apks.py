import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests

GAMES_JSON_PATH = "games.json"
APTOIDE_META_URL = "https://ws75.aptoide.com/api/7/app/getMeta/package_name={package}"

# Aptoide'de popüler oyunların "999.0" / "1000" sürümlü ~2.6MB'lık sahte kopyaları var.
# Sadece Aptoide'nin TRUSTED işaretlediği APK'ları kabul ediyoruz.
MIN_APK_SIZE = 512 * 1024
FAKE_VERSIONS = {"999", "999.0", "1000", "1000.0"}

# TRUSTED sadece virüs taraması demek; bazı mağazalar APK'ları kendi sertifikalarıyla
# yeniden imzalıyor (modlanmış/değiştirilmiş). Bu imzalayıcıları ve mağazaları reddediyoruz.
BLOCKED_STORES = {"superpocket"}
BLOCKED_SIGNERS = {
    "7D:64:F9:C2:53:C7:EF:35:A0:72:0F:6F:8A:80:2B:D4:B9:20:AA:3A",  # Jx Clarynx / anon.org
    "1C:C6:3A:91:D4:47:91:8E:EA:7E:38:04:2C:54:E6:06:8D:CA:EA:E3",  # APKMODY
}
BLOCKED_SIGNER_WORDS = ("apkmody", "anon.org", "modded", "apkpure", "happymod", "an1.com")


def fetch_meta(package: str) -> Optional[dict]:
    for attempt in range(3):
        try:
            res = requests.get(APTOIDE_META_URL.format(package=package), timeout=20)
            data = res.json()
            if data.get("info", {}).get("status") != "OK":
                return None
            return data.get("data")
        except Exception:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Aptoide'ye ulaşılamadı: {package}")


def pick_trusted_apk(meta: Optional[dict], pinned_sha1: Optional[str]) -> Optional[dict]:
    if not meta:
        return None

    f = meta.get("file") or {}
    rank = (f.get("malware") or {}).get("rank")
    version = str(f.get("vername") or "")
    size = f.get("filesize") or 0
    store = (meta.get("store") or {}).get("name")
    sig = f.get("signature") or {}
    sha1 = sig.get("sha1")
    owner = (sig.get("owner") or "").lower()

    if rank != "TRUSTED" or version in FAKE_VERSIONS or size < MIN_APK_SIZE:
        return None
    if not f.get("path") or not sha1:
        return None
    if store in BLOCKED_STORES or sha1 in BLOCKED_SIGNERS:
        return None
    if any(word in owner for word in BLOCKED_SIGNER_WORDS):
        return None
    # İlk kabul edilen imza sabitlenir; sonradan farklı imzalı bir APK gelirse reddedilir.
    if pinned_sha1 and sha1 != pinned_sha1:
        print(f"  ! imza degisti, reddedildi: {meta.get('package')} ({store})")
        return None

    obb = meta.get("obb") or {}
    main_obb = (obb.get("main") or {}).get("path")

    return {
        "path": f.get("path"),
        "path_alt": f.get("path_alt"),
        "info": {
            "source": "aptoide",
            "store": store,
            "version": version,
            "versionCode": f.get("vercode"),
            "size": f"{round(size / (1024 * 1024), 1)}MB",
            "md5": f.get("md5sum"),
            "signatureSha1": sha1,
            "signer": sig.get("owner"),
            "obbUrl": main_obb,
        },
    }


def fetch_github_apk(repo: str, asset_pattern: str = r"\.apk$") -> Optional[dict]:
    """Açık kaynak uygulamalar (ör. Winlator) için GitHub'daki son sürümün dosyasını bulur."""
    res = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=20)
    if res.status_code != 200:
        return None
    release = res.json()
    for asset in release.get("assets", []):
        if re.search(asset_pattern, asset.get("name", "")):
            return {
                "path": asset["browser_download_url"],
                "info": {
                    "source": "github",
                    "repo": repo,
                    "assetPattern": asset_pattern,
                    "version": release.get("tag_name", "").lstrip("v"),
                    "size": f"{round(asset.get('size', 0) / (1024 * 1024), 1)}MB",
                },
            }
    return None


def main() -> None:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data.get("games", [])

    def is_github(g: dict) -> bool:
        return ((g.get("downloadLinks") or {}).get("apkInfo") or {}).get("source") == "github"

    # Ücretli oyunların Aptoide kopyası korsandır, onları hiç sorgulamıyoruz.
    packages = [
        None if is_github(g) or (g.get("details") or {}).get("isFree") is False else g.get("package")
        for g in games
    ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = list(pool.map(lambda p: fetch_meta(p) if p else None, packages))

    found = 0
    for game, meta in zip(games, metas):
        dl = game.setdefault("downloadLinks", {})
        if is_github(game):
            info = dl["apkInfo"]
            gh_apk = fetch_github_apk(info["repo"], info.get("assetPattern") or r"\.apk$")
            if gh_apk:
                found += 1
                dl["load1"] = gh_apk["path"]
                dl["apkInfo"] = gh_apk["info"]
                game.setdefault("details", {})["version"] = gh_apk["info"]["version"]
            continue
        if "winlator" in (game.get("requires") or []):
            # Winlator ile çalışan oyunların linkleri elle yönetilir, Aptoide'de aranmaz.
            continue

        pinned = (dl.get("apkInfo") or {}).get("signatureSha1")
        apk = pick_trusted_apk(meta, pinned)

        if apk:
            found += 1
            dl["load1"] = apk["path"]
            dl["load2"] = apk["path_alt"] if apk["path_alt"] != apk["path"] else None
            dl["apkInfo"] = apk["info"]
        elif pinned:
            # Önceden doğrulanmış imzayı kaybetmemek için sadece linkleri kapatıyoruz.
            dl["load1"] = None
            dl["load2"] = None
            dl["apkInfo"] = {"signatureSha1": pinned}
        else:
            dl["load1"] = None
            dl["load2"] = None
            dl.pop("apkInfo", None)

    # Winlator gerektiren oyunlarda ikinci link (load2) her zaman Winlator'ın güncel APK'sıdır.
    winlator = next((g for g in games if g.get("id") == "winlator"), None)
    winlator_url = ((winlator or {}).get("downloadLinks") or {}).get("load1")
    for game in games:
        if winlator_url and "winlator" in (game.get("requires") or []):
            game["downloadLinks"]["load2"] = winlator_url

    # Web sitesi (game-guard) indirme linki olarak apk1/apk2 alanlarını okuyor.
    for game in games:
        dl = game.setdefault("downloadLinks", {})
        dl["apk1"] = dl.get("load1")
        dl["apk2"] = dl.get("load2")

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")

    print(f"Güvenilir APK bulunan oyun: {found}/{len(games)}")


if __name__ == "__main__":
    main()
