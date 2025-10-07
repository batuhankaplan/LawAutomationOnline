# UYAP Avukat Dosya Aktarıcı - Chrome Extension

UYAP Avukat Bilgi Sistemi'nden dosyalarınızı otomatik olarak kendi hukuk otomasyon sisteminize aktaran Chrome Extension.

## 🚀 Özellikler

- ✅ **Otomatik Veri Çekme**: UYAP'tan dosya bilgilerini otomatik olarak çeker
- ✅ **Akıllı Eşleştirme**: UYAP verilerini sisteminizin formatına otomatik dönüştürür
- ✅ **Toplu Aktarım**: Birden fazla dosyayı tek seferde aktarabilirsiniz
- ✅ **Belge İndirme**: UYAP'taki belgeleri otomatik olarak indirir ve sisteminize yükler
- ✅ **Müvekkil/Karşı Taraf**: Tüm taraf bilgilerini otomatik aktarır
- ✅ **Vekil Bilgileri**: Karşı taraf vekil bilgilerini kaydeder
- ✅ **Duruşma Bilgileri**: Duruşma tarihleri otomatik eklenir
- ✅ **Güvenli**: Verileriniz direkt sizin sunucunuza gönderilir

## 📋 Gereksinimler

- Google Chrome veya Chromium tabanlı tarayıcı
- UYAP Avukat Bilgi Sistemi hesabı (E-imza ile giriş)
- Çalışan hukuk otomasyon sisteminiz (Flask backend)

## 🔧 Kurulum

### 1. Extension'ı Yükleme

1. Bu klasörü (`uyap_chrome_extension`) bilgisayarınıza indirin
2. Chrome'da `chrome://extensions/` adresine gidin
3. Sağ üst köşeden **Geliştirici modunu** açın
4. **Paketlenmemiş uzantı yükle** butonuna tıklayın
5. `uyap_chrome_extension` klasörünü seçin

### 2. Backend API Kurulumu

Flask uygulamanız zaten gerekli API endpoint'lerini içeriyor:

- `/api/check_auth` - Authentication kontrolü
- `/api/import_from_uyap` - Dosya aktarma
- `/api/upload_uyap_document/<case_id>` - Belge yükleme

**NOT:** Bu API'ler `app.py` dosyasına eklenmiştir (satır 9929-10208).

### 3. CORS Ayarları

Flask uygulamanızda CORS ayarlarını yapılandırın (gerekirse):

```python
from flask_cors import CORS

# Chrome Extension için izin ver
CORS(app, resources={
    r"/api/*": {
        "origins": ["chrome-extension://*"],
        "supports_credentials": True
    }
})
```

### 4. Extension Ayarları

Extension'ı ilk açtığınızda:

1. ⚙️ **Ayarlar** sekmesine gidin
2. **API URL** alanına backend URL'inizi girin (örn: `http://localhost:5000` veya `https://yourdomain.com`)
3. **Ayarları Kaydet** butonuna tıklayın
4. **Bağlantıyı Test Et** ile kontrol edin

## 📖 Kullanım

### Adım 1: UYAP'a Giriş Yapın

1. E-imza ile [UYAP Avukat Bilgi Sistemi](https://avukat.uyap.gov.tr)'ne giriş yapın
2. **Dosya Sorgulama İşlemleri > Dosya Sorgulama** sayfasına gidin

### Adım 2: Sisteminize Giriş Yapın

1. Kendi hukuk otomasyon sisteminize giriş yapın
2. Extension'ın sisteminizle bağlantılı olduğundan emin olun (yeşil durum işareti)

### Adım 3: Dosyaları Tarayın

1. UYAP'ta dosya sorgulama yaptığınız sayfada extension popup'ını açın
2. **Sayfayı Tara** butonuna tıklayın
3. Sayfadaki tüm dosyalar listelenecek

### Adım 4: Aktarım Yapın

#### Tek Dosya Aktarma:
- Listeden bir dosyaya tıklayın
- Detay sayfası açılacak
- Extension otomatik olarak tüm bilgileri çekecek
- **Sisteme Aktar** butonuna tıklayın

#### Toplu Aktarma:
1. Aktarmak istediğiniz dosyaları seçin (checkbox)
2. **Seçili Dosyaları Aktar** butonuna tıklayın
3. İlerleme çubuğundan durumu takip edin

### Adım 5: Belgeleri Kontrol Edin

Extension, UYAP'taki belgeleri de otomatik olarak indirir ve sisteminize yükler. Bu işlem arka planda gerçekleşir.

## 🔍 Veri Eşleştirme

Extension aşağıdaki verileri otomatik eşleştirir:

| UYAP Alanı | Sistem Alanı |
|------------|--------------|
| Yargı Türü (Hukuk, Ceza, İcra) | Dosya Türü |
| Mahkeme Adı | Adliye/Birim |
| Esas No (YYYY/NUM) | Yıl + Dosya No |
| Taraflar | Müvekkil + Karşı Taraf |
| Vekileler | Karşı Taraf Vekili |
| Belgeler | Dosya Belgeleri |
| Duruşma Tarihleri | Sonraki Duruşma |

## ⚙️ Yapılandırma

### config.js Dosyası

Extension ayarlarını `config.js` dosyasından özelleştirebilirsiniz:

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:5000',

    // Dosya türü eşleştirmeleri
    COURT_TYPE_MAPPING: {
        'Hukuk': 'hukuk',
        'Ceza': 'ceza',
        'İcra': 'icra',
        // ...
    },

    // Belge türü eşleştirmeleri
    DOCUMENT_TYPE_MAPPING: {
        'Dilekçe': 'Dilekçe',
        'Karar': 'Karar',
        // ...
    }
};
```

## 🐛 Sorun Giderme

### Extension UYAP sayfasında çalışmıyor
- Sayfayı yenileyin (F5)
- Extension'ı devre dışı bırakıp tekrar etkinleştirin
- Chrome'u yeniden başlatın

### "Bağlantı hatası" alıyorum
- Backend URL'inin doğru olduğundan emin olun
- Backend sunucusunun çalıştığını kontrol edin
- CORS ayarlarının yapıldığından emin olun

### Dosyalar aktarılmıyor
- Sisteminize giriş yaptığınızdan emin olun
- Browser Console'u açın (F12) ve hata mesajlarını kontrol edin
- Backend loglarını inceleyin

### Belgeler indirilmiyor
- UYAP oturumunuzun açık olduğundan emin olun
- İnternet bağlantınızı kontrol edin
- Belge indirme URL'lerinin geçerli olduğundan emin olun

## 🔒 Güvenlik

- ✅ Tüm veriler HTTPS üzerinden şifrelenir (production'da)
- ✅ Extension sadece UYAP ve kendi backend'inizle iletişim kurar
- ✅ Kimlik bilgileri tarayıcıda saklanır, 3. taraflara gönderilmez
- ✅ API istekleri authentication ile korunur

## 📝 Sınırlamalar

- Extension sadece tarayıcıda UYAP oturumu açıkken çalışır
- UYAP'ın HTML yapısı değişirse content script güncellemesi gerekir
- Toplu aktarımlarda UYAP API limitlerine dikkat edilmelidir
- Çok büyük belgeler (>10MB) indirme hatası verebilir

## 🆕 Versiyon Geçmişi

### v1.0.0 (2025-01-06)
- ✨ İlk sürüm
- ✅ Dosya listesi tarama
- ✅ Tek ve toplu dosya aktarma
- ✅ Belge indirme ve yükleme
- ✅ Müvekkil/Karşı taraf/Vekil eşleştirme
- ✅ Duruşma bilgisi aktarma

## 🤝 Destek

Sorunlarınız için:
1. Browser Console loglarını kontrol edin (F12)
2. Backend loglarını inceleyin
3. Extension'ı yeniden yükleyin
4. Chrome'u yeniden başlatın

## 📜 Lisans

Bu extension, Law Automation Online sisteminizin bir parçasıdır. Kendi kullanımınız için özgürce kullanabilirsiniz.

---

**Geliştirici:** Law Automation Online Ekibi
**Versiyon:** 1.0.0
**Son Güncelleme:** Ocak 2025
