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
  "platform": "windows",            // opsiyonel; yoksa Android
  "requires": ["winlator"],         // opsiyonel; once kurulmasi gereken kayitlarin id'leri
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
    "pcStoreUrls": ["..."],         // PC oyunlari icin resmi magazalar (Steam, Epic...)
    "webpage": ["..."],
    "load1": "...",                 // dogrulanmis APK / dosya linki veya null
    "load2": null,
    "apkInfo": { "source": "aptoide|github", "version": "...", "size": "...", "md5": "...",
                 "signatureSha1": "...", "signer": "...", "obbUrl": null }
  }
}
```

### Winlator gerektiren PC oyunlari

`platform: "windows"` ve `requires: ["winlator"]` olan kayitlarda uygulama:

1. Karta "PC · Winlator gerekli" rozeti koyar.
2. Cihazda `com.winlator` kurulu degilse once `winlator` kaydinin `load1` linkini acar.
3. Kuruluysa oyunun `load1` dosyasini indirir; `load1` yoksa (ucretli oyun, orn. GTA V)
   `pcStoreUrls` icindeki magazaya yonlendirir. Kullanici oyunu kendi hesabiyla alip Winlator'da acar.

Ucretli oyunlarin dosyalari **asla** eklenmez, sadece resmi magaza linkleri verilir.

## Scriptler

| Script | Ne yapar |
|---|---|
| `update_apks.py` | Her gun GitHub Actions ile calisir. Aptoide'den sadece TRUSTED, orijinal imzali APK'lari kabul eder (yeniden imzalanmis/modlu APK'lar ve `superpocket` gibi magazalar engelli, imza SHA1'i sabitlenir). `apkInfo.source == "github"` olanlari GitHub Releases'tan gunceller. |
| `add_playstore_games.py` | Play Store'dan oyun bilgisi/gorsel ceker; Play'den kalkmis klasikleri Aptoide'den orijinal imzayla ekler; kalkmis oyunlarin Play linkini temizler. |
| `add_special_games.py` | Winlator ile oynanan PC oyunlarini ve GitHub'dan resmi APK'si olan acik kaynak oyunlari ekler. |

Kurulum: `python -m pip install requests google-play-scraper pillow`
