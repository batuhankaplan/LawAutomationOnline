# UYAP Entegrasyon Sistemi - Hızlı Başlangıç Kılavuzu

## 🎯 Genel Bakış

UYAP Avukat Bilgi Sistemi'nden dosyalarınızı otomatik olarak kendi hukuk otomasyon sisteminize aktaran Chrome Extension hazırlandı.

## 📁 Sistem Dosyaları

### Chrome Extension Dosyaları
```
uyap_chrome_extension/
├── manifest.json           # Extension yapılandırması
├── content.js              # UYAP sayfalarından veri çekme
├── background.js           # API iletişimi
├── popup.html              # Extension arayüzü
├── popup.css               # UI stilleri
├── popup.js                # UI mantığı
├── config.js               # Ayarlar ve eşleştirmeler
├── mapper.js               # Veri dönüştürme
├── README.md               # Detaylı dokümantasyon
└── icons/                  # Extension ikonları
    ├── icon.svg
    └── README.txt
```

### Backend API (app.py)
```python
# Satır 9929-10208
/api/check_auth              # Authentication kontrolü
/api/import_from_uyap        # Dosya aktarma
/api/upload_uyap_document    # Belge yükleme
```

## 🚀 Kurulum Adımları

### 1. Chrome Extension Kurulumu

```bash
# 1. Chrome'da extensions sayfasını açın
chrome://extensions/

# 2. Geliştirici modunu açın (sağ üst)

# 3. "Paketlenmemiş uzantı yükle" butonuna tıklayın

# 4. uyap_chrome_extension klasörünü seçin
```

### 2. Extension İlk Ayarları

1. Extension ikonuna tıklayın
2. **⚙️ Ayarlar** sekmesine gidin
3. **API URL** alanına backend URL'inizi girin:
   - Localhost: `http://localhost:5000`
   - Production: `https://yourdomain.com`
4. **💾 Ayarları Kaydet** butonuna tıklayın
5. **🔌 Bağlantıyı Test Et** ile kontrol edin

### 3. İkon Dosyalarını Oluşturma (Opsiyonel)

Extension çalışır ancak özel ikonlar için:

```bash
# Yöntem 1: ImageMagick ile
cd uyap_chrome_extension/icons
convert -background none icon.svg -resize 16x16 icon16.png
convert -background none icon.svg -resize 48x48 icon48.png
convert -background none icon.svg -resize 128x128 icon128.png

# Yöntem 2: Online araç
# https://svgtopng.com/ adresine icon.svg dosyasını yükleyin
# 16x16, 48x48, 128x128 boyutlarında PNG indirin
```

## 📖 Kullanım

### Senaryo 1: Tek Dosya Aktarma

1. **UYAP'a giriş yapın**
   - https://avukat.uyap.gov.tr
   - E-imza ile giriş

2. **Dosya Sorgulama**
   - Dosya Sorgulama İşlemleri > Dosya Sorgulama
   - Yargı türü ve mahkeme seçin
   - Sorguya basın

3. **Extension'ı açın**
   - Extension ikonuna tıklayın
   - **Sayfayı Tara** butonuna tıklayın

4. **Dosya seçin ve aktarın**
   - Listeden bir dosyaya tıklayın (otomatik detay çeker)
   - Veya doğrudan checkbox ile seçin
   - **Seçili Dosyaları Aktar** butonuna tıklayın

### Senaryo 2: Toplu Dosya Aktarma

1. **UYAP'ta dosya listesi görüntüleyin**
   - Tüm dosyalarınızı sorgulayın

2. **Extension'da tara**
   - Sayfayı Tara butonuna basın

3. **Toplu seçim**
   - **Tümünü Seç** checkbox'ını işaretleyin
   - Veya tek tek dosyaları seçin

4. **Toplu aktar**
   - **Seçili Dosyaları Aktar** (örn: 15 dosya)
   - İlerleme çubuğundan takip edin
   - Sonuçları kontrol edin

## 🔄 Veri Akışı

```
UYAP Sistemi
    ↓
[Content Script] → DOM'dan veri çekme
    ↓
[Mapper] → UYAP formatını sistem formatına dönüştürme
    ↓
[Background Worker] → API'ye gönderme
    ↓
[Flask Backend] → /api/import_from_uyap
    ↓
[Database] → CaseFile tablosuna kaydetme
    ↓
[Belgeler] → /api/upload_uyap_document (otomatik)
```

## 📊 Aktarılan Veriler

### Dosya Bilgileri
- ✅ Dosya türü (Hukuk, Ceza, İcra, Savcılık, vb.)
- ✅ Mahkeme/Adliye bilgisi
- ✅ Esas No (Yıl + Dosya No)
- ✅ Açılış tarihi
- ✅ Dosya durumu

### Taraf Bilgileri
- ✅ **Ana Müvekkil**: Ad, TC/Vergi No, Telefon, Adres, Sıfat
- ✅ **Ek Müvekkiller**: Sınırsız sayıda (JSON)
- ✅ **Ana Karşı Taraf**: Ad, TC/Vergi No, Telefon, Adres, Sıfat
- ✅ **Ek Karşı Taraflar**: Sınırsız sayıda (JSON)

### Vekil Bilgileri
- ✅ Karşı taraf vekili: Ad, Baro, Sicil No, Telefon, Adres

### Belgeler
- ✅ Tüm belge türleri (Dilekçe, Karar, Tutanak, vb.)
- ✅ Otomatik indirme ve yükleme
- ✅ Belge tarihleri

### Duruşma Bilgileri
- ✅ Sonraki duruşma tarihi ve saati
- ✅ Duruşma türü (fiziki/e-duruşma)

## ⚙️ Özelleştirme

### config.js - Veri Eşleştirmeleri

```javascript
// Dosya türü eşleştirme
COURT_TYPE_MAPPING: {
    'Hukuk': 'hukuk',
    'Ceza': 'ceza',
    'İcra': 'icra',
    // Eklemek isterseniz buraya ekleyin
}

// Belge türü eşleştirme
DOCUMENT_TYPE_MAPPING: {
    'Dilekçe': 'Dilekçe',
    'Karar': 'Karar',
    // Özel belge türlerinizi ekleyin
}

// API URL
API_BASE_URL: 'http://localhost:5000'
```

### mapper.js - Özel Dönüşüm Mantığı

Eğer UYAP'taki alan isimleri değişirse veya özel dönüşüm mantığı eklemek isterseniz `mapper.js` dosyasındaki fonksiyonları düzenleyin.

## 🐛 Sorun Giderme

### Problem: Extension UYAP'ta görünmüyor

**Çözüm:**
```bash
1. Sayfayı yenileyin (F5)
2. Extension'ı devre dışı bırakıp tekrar etkinleştirin
3. Chrome'u yeniden başlatın
4. Chrome DevTools Console'u açın (F12) ve hataları kontrol edin
```

### Problem: "Bağlantı hatası" alıyorum

**Çözüm:**
```bash
1. Backend sunucusunun çalıştığını kontrol edin:
   python app.py

2. API URL'ini kontrol edin (Extension > Ayarlar)

3. CORS ayarlarını kontrol edin:
   - Flask app'te CORS kurulu olmalı
   - chrome-extension://* origin'ine izin verilmeli

4. Sisteme giriş yaptığınızdan emin olun
```

### Problem: Dosyalar aktarılmıyor

**Çözüm:**
```bash
1. Browser Console loglarını kontrol edin (F12 > Console)

2. Backend loglarını kontrol edin:
   # Terminal'de Flask output

3. API endpoint'lerinin çalıştığını test edin:
   curl http://localhost:5000/api/check_auth

4. Authentication'ın geçerli olduğunu kontrol edin
```

### Problem: Belgeler indirilmiyor

**Çözüm:**
```bash
1. UYAP oturumunun açık olduğundan emin olun

2. Belge indirme URL'lerinin geçerli olduğunu kontrol edin

3. Network sekmesinde (F12 > Network) istekleri inceleyin

4. UYAP'ın belge indirme sistemini kontrol edin
```

## 🔒 Güvenlik Notları

- ✅ Extension sadece UYAP ve kendi backend'inizle iletişim kurar
- ✅ Hiçbir veri 3. taraf servislere gönderilmez
- ✅ Kimlik bilgileri tarayıcıda saklanır
- ✅ API istekleri authentication ile korunur
- ✅ Production'da HTTPS kullanın

## 📝 Gelecek Geliştirmeler

Sisteme eklenebilecek özellikler:

1. **Otomatik Senkronizasyon**
   - Günde 1 kez otomatik UYAP kontrolü
   - Yeni dosyaları otomatik çekme

2. **Bildirim Sistemi**
   - Yeni dosya eklendiğinde bildirim
   - Duruşma hatırlatmaları

3. **Gelişmiş Filtreleme**
   - Sadece belirli tarihteki dosyaları çek
   - Dosya türüne göre filtrele

4. **Toplu Belge İndirme**
   - Tüm dosyaların belgelerini tek seferde indir
   - ZIP olarak kaydet

5. **UYAP İzleme**
   - Dosya değişikliklerini takip et
   - Yeni karar/belge bildirimları

## 📞 Destek

Sistem ile ilgili sorularınız için:

1. **README.md** - Detaylı dokümantasyon
2. **Browser Console** - F12 ile logları kontrol edin
3. **Backend Logs** - Flask terminal output
4. **GitHub Issues** - Hata bildirimi

## 🎉 Başarılı Kurulum Testi

Extension'ın düzgün çalıştığını kontrol etmek için:

```bash
✅ 1. Chrome'da extension görünüyor mu?
✅ 2. Extension popup açılıyor mu?
✅ 3. Ayarlar kaydediliyor mu?
✅ 4. Bağlantı testi başarılı mı?
✅ 5. UYAP sayfasında "Sisteme Aktar" butonu var mı?
✅ 6. Sayfa tarama çalışıyor mu?
✅ 7. Tek dosya aktarımı çalışıyor mu?
✅ 8. Toplu aktarım çalışıyor mu?
✅ 9. Aktarılan dosya sistemde görünüyor mu?
✅ 10. Belgeler yükleniyor mu?
```

Hepsi ✅ ise sistem hazır!

---

**Geliştirme Tarihi:** 6 Ocak 2025
**Versiyon:** 1.0.0
**Geliştirici:** Law Automation Online Ekibi
