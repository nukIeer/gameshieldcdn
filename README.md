# gameshieldcdn

Best Games & Shield uygulamasi icin oyun verisi (`games.json`) ve gorsel deposu.

JSON adresi:

```
https://cdn.jsdelivr.net/gh/nukIeer/gameshieldcdn@master/games.json
```

## Klasor Yapisi

```
games/<oyun-id>/
  icon.png             512x512
  banner.png           1024x500
  screenshots/1.jpg ...
```

## Oyun Kaydi

```json
{
  "id": "roblox",
  "title": "Roblox",
  "package": "com.roblox.client",
  "requires": ["winlator"],         // opsiyonel; oyun bu APK'nin icinde calisir, once o kurulur
  "tags": ["nostalgia"],            // opsiyonel; "nostalgia", "emulator"
  "details": {
    "downloads": "1B+", "rating": 4.38, "size": "137.0MB", "ageRating": "PEGI-12",
    "androidVersion": "N/A", "version": "2.727.1199",
    "isFree": true                  // ucretli oyunlarda false; APK linki hic verilmez
  },
  "description": "...",
  "whatsNew": "...",
  "media": { "iconUrl": "...", "bannerUrl": "...", "screenshots": ["..."] },
  "downloadLinks": {
    "playStoreUrl": "...",          // Play Store'dan kalkmis oyunlarda null
    "galaxyStoreUrl": "...",
    "pcStoreUrls": ["..."],         // Winlator oyunlarinin resmi magazalari (Steam, Epic...)
    "webpage": ["https://game-guard-three.vercel.app/game/<oyun-id>"],
    "load1": "...",                 // dogrulanmis APK / dosya linki veya null
    "load2": null,                  // Winlator oyunlarinda Winlator APK'si
    "apk1": "...", "apk2": null,    // load1/load2'nin kopyasi; web sitesi bu alanlari okuyor
    "apkInfo": { "source": "aptoide|github", "version": "...", "size": "...", "md5": "...",
                 "signatureSha1": "...", "signer": "...", "obbUrl": null }
  }
}
```

### Winlator ile calisan oyunlar

Winlator bir Android APK'sidir; `requires: ["winlator"]` olan oyunlar telefonda onun icinde calisir.
Bu kayitlarda uygulama:

- `load1`: oyunun kendisi (ucretsizse dosya, ucretliyse resmi magaza sayfasi; orn. GTA V -> Steam)
- `load2`: Winlator APK'si. `update_apks.py` her gun Winlator'in guncel linkini buraya yazar.

Kullanici once 2. linkten Winlator'i kurar, sonra 1. linkten oyunu alip Winlator'da acar.
Ucretli oyunlarda kullanici oyunu kendi hesabiyla satin alir.

Ucretli oyunlarin dosyalari **asla** eklenmez, sadece resmi magaza linkleri verilir.

## Scriptler

| Script | Ne yapar |
|---|---|
| `update_apks.py` | Her gun GitHub Actions ile calisir. Aptoide'den sadece TRUSTED, orijinal imzali APK'lari kabul eder (yeniden imzalanmis/modlu APK'lar ve `superpocket` gibi magazalar engelli, imza SHA1'i sabitlenir). `apkInfo.source == "github"` olanlari GitHub Releases'tan gunceller. |
| `add_playstore_games.py` | Play Store'dan oyun bilgisi/gorsel ceker; Play'den kalkmis klasikleri Aptoide'den orijinal imzayla ekler; kalkmis oyunlarin Play linkini temizler. |
| `enrich_details.py` | Eksik puan/indirme/boyut/Android surumunu Play Store, Aptoide, Steam ve GitHub'dan doldurur (gunluk workflow'da da calisir). Veri yoksa uydurmaz. |
| `reorder_games.py` | Liste sirasini belirler: `TOP` vitrin listesi (Roblox, Winlator, GTA V, ...), sonra indirme/puana gore, taklitler en sonda. Yeni oyunu one almak icin `TOP`'a ekle. |
| `add_special_games.py` | Winlator ile oynanan oyunlari ve GitHub'dan resmi APK'si olan acik kaynak oyunlari ekler. |

Kurulum: `python -m pip install requests google-play-scraper pillow`
