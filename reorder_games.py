"""games.json sırasını belirler (uygulama listeyi bu sırayla gösterir, ilk oyun öne çıkan oyundur).

1. TOP listesi: elle seçilmiş vitrin sırası
2. Geri kalanlar: indirme sayısı, sonra puana göre
3. KNOCKOFFS: ünlü oyun adlarını taklit eden kopyalar en sona
"""
import json
import re

GAMES_JSON_PATH = "games.json"

TOP = [
    "roblox", "winlator", "gta5", "steamlink", "geforcenow", "subwaysurfers", "minecraftpe", "freefire", "supercell", "pubg",
    "gtasanandreas", "among", "clashofclans", "mytalkingtom", "8", "candycrush", "codmobile",
    "clashroyale", "hill", "templerun2", "mobilelegends", "gtavicecity", "pokemongo", "stickman",
    "block", "gamotronix", "carparking", "standoff2", "minionrush", "jetpackjoyride", "fruitninja",
    "my", "pou", "free", "asphalt", "hillclimb2", "gtalibertycity", "gtachinatown", "gta3",
    "shadowfight2", "granny", "pvz", "hungryshark", "crossyroad", "sniper3d", "gangstarvegas",
    "asphalt8", "flappybird", "geometry", "slither", "traffic", "trafficracer",
]

# Ünlü oyunların adını kullanan taklitler (asıl oyunlar TOP listesinde).
KNOCKOFFS = ["minecraft", "subway", "welcome"]


def downloads_value(text: str) -> int:
    m = re.match(r"(\d+)([KMB])\+", text or "")
    if not m:
        return 0
    return int(m.group(1)) * {"K": 10**3, "M": 10**6, "B": 10**9}[m.group(2)]


def main() -> None:
    with open(GAMES_JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    games = data["games"]
    by_id = {g["id"]: g for g in games}

    top = [by_id[i] for i in TOP if i in by_id]
    tail = [by_id[i] for i in KNOCKOFFS if i in by_id]
    fixed = {g["id"] for g in top + tail}
    rest = sorted(
        (g for g in games if g["id"] not in fixed),
        key=lambda g: (downloads_value(g["details"].get("downloads")), g["details"].get("rating") or 0),
        reverse=True,
    )
    data["games"] = top + rest + tail

    with open(GAMES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print([g["id"] for g in data["games"]][:15])


if __name__ == "__main__":
    main()
