"""games.json sırasını belirler (uygulama listeyi bu sırayla gösterir, ilk oyun öne çıkan oyundur).

Uygulamanın farkı Play Store'da olmayanları sunmak; sıralama buna göre:
1. SHOWCASE: en üstteki vitrin (Roblox, Winlator, GTA V)
2. Play Store'da olmayanlar ve Winlator ile oynananlar ("exclusive" etiketi alır)
3. HITS: Play Store'da da olan ama herkesin bildiği büyük oyunlar
4. Play Store'da zaten olan sıradan oyunlar
(2 ve 4'te: direkt APK'sı olan önce, sonra indirme sayısı, sonra puan)
5. KNOCKOFFS: ünlü oyun adlarını taklit eden kopyalar en sona
"""
import json
import re

GAMES_JSON_PATH = "games.json"

SHOWCASE = ["roblox", "winlator", "gta5"]

HITS = [
    "steamlink", "geforcenow", "subwaysurfers", "minecraftpe", "freefire", "supercell",
    "gtasanandreas", "among", "clashofclans", "mytalkingtom", "8", "candycrush", "codmobile",
    "clashroyale", "templerun2", "mobilelegends", "gtavicecity", "pokemongo",
    "block", "gamotronix", "carparking", "standoff2", "minionrush", "jetpackjoyride", "fruitninja",
    "my", "pou", "free", "asphalt", "hillclimb2", "gtalibertycity", "gtachinatown", "gta3",
    "shadowfight2", "granny", "pvz", "hungryshark", "crossyroad", "sniper3d", "gangstarvegas",
    "asphalt8", "geometry",
]

# Ünlü oyunların adını kullanan taklitler.
KNOCKOFFS = ["minecraft", "subway", "welcome"]


def downloads_value(text: str) -> int:
    m = re.match(r"(\d+)([KMB])\+", text or "")
    if not m:
        return 0
    return int(m.group(1)) * {"K": 10**3, "M": 10**6, "B": 10**9}[m.group(2)]


def popularity(g: dict):
    has_apk = bool((g.get("downloadLinks") or {}).get("load1"))
    return has_apk, downloads_value(g["details"].get("downloads")), g["details"].get("rating") or 0


def is_exclusive(g: dict) -> bool:
    return not (g.get("downloadLinks") or {}).get("playStoreUrl") or "winlator" in (g.get("requires") or [])


def main() -> None:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data["games"]
    by_id = {g["id"]: g for g in games}

    showcase = [by_id[i] for i in SHOWCASE if i in by_id]
    tail = [by_id[i] for i in KNOCKOFFS if i in by_id]
    taken = {g["id"] for g in showcase + tail}

    exclusives = sorted((g for g in games if g["id"] not in taken and is_exclusive(g)), key=popularity, reverse=True)
    taken |= {g["id"] for g in exclusives}
    hits = [by_id[i] for i in HITS if i in by_id and i not in taken]
    taken |= {g["id"] for g in hits}
    filler = sorted((g for g in games if g["id"] not in taken), key=popularity, reverse=True)

    # "exclusive" etiketi her çalıştırmada yeniden hesaplanır.
    for g in games:
        tags = [t for t in g.get("tags") or [] if t != "exclusive"]
        if is_exclusive(g) and g["id"] not in KNOCKOFFS:
            tags.append("exclusive")
        if tags:
            g["tags"] = tags
        else:
            g.pop("tags", None)

    data["games"] = showcase + exclusives + hits + filler + tail

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print(f"vitrin {len(showcase)} | exclusive {len(exclusives)} | hit {len(hits)} | diger {len(filler)} | taklit {len(tail)}")


if __name__ == "__main__":
    main()
