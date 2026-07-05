# gameshieldcdn

Best Games & Shield uygulamasi icin gorsel varlik deposu.

## Klasor Yapisi

```
games/
  <oyun-id>/
    icon.png    -- 512x512 PNG, app ikonu
    banner.png  -- 1024x500 PNG, detay ekrani banner
```

## Gorsel URL Formati

```
https://raw.githubusercontent.com/nukIeer/gameshieldcdn/master/games/<oyun-id>/icon.png
https://raw.githubusercontent.com/nukIeer/gameshieldcdn/master/games/<oyun-id>/banner.png
```

## Mevcut Oyunlar

| ID          | Klasor              | Icon | Banner |
|-------------|---------------------|------|--------|
| roblox      | games/roblox/       | [ ]  | [ ]    |
| minecraft   | games/minecraft/    | [ ]  | [ ]    |
| freefire    | games/freefire/     | [ ]  | [ ]    |
| pubg        | games/pubg/         | [ ]  | [ ]    |
| brawlstars  | games/brawlstars/   | [ ]  | [ ]    |

## Gorsel Ekleme

1. games/<oyun-id>/ klasorune icon.png ve banner.png koy
2. git add / commit / push yap
3. games.json Gist'ini yukardaki URL formatiyla guncelle
4. Uygulama canli olarak yeni gorselleri ceker (guncelleme gerekmez)

## Gist games.json Ornegi

```json
{
  "games": [
    {
      "id": "roblox",
      "title": "Roblox",
      "description": "Roblox, milyonlarca oyun barindiran devasa bir oyun platformudur.",
      "iconUrl": "https://raw.githubusercontent.com/nukIeer/gameshieldcdn/master/games/roblox/icon.png",
      "bannerUrl": "https://raw.githubusercontent.com/nukIeer/gameshieldcdn/master/games/roblox/banner.png",
      "playStoreUrl": "https://play.google.com/store/apps/details?id=com.roblox.client",
      "galaxyStoreUrl": "https://galaxystore.samsung.com/detail/com.roblox.client",
      "tapTapUrl": "https://www.taptap.io/app/roblox"
    }
  ]
}
```

