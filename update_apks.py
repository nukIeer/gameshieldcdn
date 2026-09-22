import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests

GAMES_JSON_PATH = "games.json"
APTOIDE_META_URL = "https://ws75.aptoide.com/api/7/app/getMeta/package_name={package}"

# Aptoide'de popüler oyunların "999.0" / "1000" sürümlü ~2.6MB'lık sahte kopyaları var.
# Sadece Aptoide'nin TRUSTED işaretlediği ve makul boyuttaki APK'ları kabul ediyoruz.
MIN_APK_SIZE = 5 * 1024 * 1024
FAKE_VERSIONS = {"999", "999.0", "1000", "1000.0"}


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


def pick_trusted_apk(meta: Optional[dict]) -> Optional[dict]:
    if not meta:
        return None

    f = meta.get("file") or {}
    rank = (f.get("malware") or {}).get("rank")
    version = str(f.get("vername") or "")
    size = f.get("filesize") or 0

    if rank != "TRUSTED" or version in FAKE_VERSIONS or size < MIN_APK_SIZE:
        return None
    if not f.get("path"):
        return None

    obb = meta.get("obb") or {}
    main_obb = (obb.get("main") or {}).get("path")

    return {
        "path": f.get("path"),
        "path_alt": f.get("path_alt"),
        "info": {
            "source": "aptoide",
            "store": (meta.get("store") or {}).get("name"),
            "version": version,
            "versionCode": f.get("vercode"),
            "size": f"{round(size / (1024 * 1024), 1)}MB",
            "md5": f.get("md5sum"),
            "obbUrl": main_obb,
        },
    }


def main() -> None:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data.get("games", [])

    packages = [g.get("package") for g in games]
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = list(pool.map(lambda p: fetch_meta(p) if p else None, packages))

    found = 0
    for game, meta in zip(games, metas):
        apk = pick_trusted_apk(meta)
        dl = game.setdefault("downloadLinks", {})

        if apk:
            found += 1
            dl["load1"] = apk["path"]
            dl["load2"] = apk["path_alt"] if apk["path_alt"] != apk["path"] else None
            dl["apkInfo"] = apk["info"]
        else:
            dl["load1"] = None
            dl["load2"] = None
            dl.pop("apkInfo", None)

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")

    print(f"Güvenilir APK bulunan oyun: {found}/{len(games)}")


if __name__ == "__main__":
    main()
