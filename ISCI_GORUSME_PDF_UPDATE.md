# İşçi Görüşme Formu PDF Güncelleme Kılavuzu

## Yapılan Değişiklikler

### 1. Database Güncellemeleri

#### Model Değişikliği (`firstwebsite/models.py`)
- `IsciGorusmeTutanagi` modeline `pdf_path` alanı eklendi
- Bu alan PDF dosyasının server'da kaydedildiği yolu tutar

#### Local SQLite Migration
```bash
python firstwebsite/isci_gorusme_pdf_migration.py
```
✅ **Tamamlandı** - Local database'e `pdf_path` kolonu eklendi

#### DigitalOcean PostgreSQL Migration
DigitalOcean'da şu komutu çalıştırın:
```bash
cd /path/to/LawAutomationOnline
source venv/bin/activate
python firstwebsite/postgresql_isci_gorusme_migration.py
```

### 2. Backend Güncellemeleri (`firstwebsite/app.py`)

#### Yeni Route: `/save_worker_interview_pdf/<int:interview_id>`
- PDF'i base64 formatında alır
- Dosya adını oluşturur: `"{İsim Soyisim} Isci Gorusme Formu.pdf"`
- PDF'i `uploads/worker_interviews/` klasörüne kaydeder
- Database'e dosya yolunu kaydeder
- Dosya URL'ini döner

#### Yeni Route: `/uploads/<path:filename>`
- Uploads klasöründen dosya servisi yapar
- PDF'lerin tarayıcıda görüntülenmesini sağlar

### 3. Frontend Güncellemeleri (`firstwebsite/templates/isci_gorusme.html`)

#### PDF Önizleme Akışı:
1. **PDF Oluştur**: HTML2PDF ile PDF oluşturulur (data URL)
2. **Backend'e Gönder**: PDF backend'e kaydedilmek üzere gönderilir
3. **Dosya Kaydet**: Backend PDF'i doğru isimle kaydeder
4. **URL Al**: Backend kaydedilen PDF'in URL'ini döner
5. **Önizle**: Kaydedilen PDF yeni sekmede açılır

#### Dosya Adı Formatı:
- **Önizleme**: `{İsim Soyisim} İşçi Görüşme Formu.pdf`
- **Backend**: `{İsim Soyisim} Isci Gorusme Formu.pdf`

### 4. Dosya Yapısı

```
firstwebsite/
├── uploads/
│   └── worker_interviews/
│       ├── Kaplan Isci Gorusme Formu.pdf
│       ├── Ahmet Yilmaz Isci Gorusme Formu.pdf
│       └── ...
├── models.py (güncellendi)
├── app.py (güncellendi)
├── templates/
│   └── isci_gorusme.html (güncellendi)
├── isci_gorusme_pdf_migration.py (yeni)
└── postgresql_isci_gorusme_migration.py (yeni)
```

## Deployment Adımları

### Local Test (✅ Tamamlandı)
1. Migration çalıştırıldı
2. Backend route'ları eklendi
3. Frontend güncellendi
4. Test edildi

### GitHub'a Push
```bash
git add .
git commit -m "İşçi görüşme formu PDF kaydetme özelliği eklendi"
git push origin main
```

### DigitalOcean Deployment

1. **SSH ile bağlan**:
```bash
ssh root@your-digitalocean-server
```

2. **Kodu çek**:
```bash
cd /var/www/lawautomation  # veya uygulamanızın yolu
git pull origin main
```

3. **Virtual environment'i aktifleştir**:
```bash
source venv/bin/activate
```

4. **PostgreSQL migration'ı çalıştır**:
```bash
python firstwebsite/postgresql_isci_gorusme_migration.py
```

5. **Uploads klasörünü oluştur** (yoksa):
```bash
mkdir -p firstwebsite/uploads/worker_interviews
chmod 755 firstwebsite/uploads/worker_interviews
```

6. **Uygulamayı yeniden başlat**:
```bash
systemctl restart lawautomation
```

7. **Logları kontrol et**:
```bash
journalctl -u lawautomation -f
```

## Önemli Notlar

### Güvenlik
- PDF'ler `uploads/worker_interviews/` klasöründe saklanır
- Sadece login olan kullanıcılar PDF kaydedebilir
- Dosya adları güvenli karakterlere dönüştürülür

### Dosya İsimlendirme
- Türkçe karakterler korunur
- Geçersiz karakterler temizlenir
- Her işçi için benzersiz isim: `{İsim Soyisim} Isci Gorusme Formu.pdf`

### Database
- SQLite (Local): `pdf_path VARCHAR(500)`
- PostgreSQL (Live): `pdf_path VARCHAR(500)`

## Test Senaryosu

1. ✅ Yeni form oluştur
2. ✅ Form doldur
3. ✅ "PDF Önizle" butonuna bas
4. ✅ PDF backend'e kaydedilir
5. ✅ Doğru isimle kaydedildiğini doğrula
6. ✅ Yeni sekmede PDF görüntülenir
7. ✅ Tarayıcının indirme butonu ile indir
8. ✅ Dosya adının doğru olduğunu kontrol et

## Sorun Giderme

### PDF kaydedilmiyor
- Backend loglarını kontrol et: `journalctl -u lawautomation -f`
- Uploads klasörü izinlerini kontrol et: `ls -la firstwebsite/uploads/`

### PDF açılmıyor
- `/uploads/<path:filename>` route'unun çalıştığını kontrol et
- Dosyanın fiziksel olarak var olduğunu kontrol et

### Migration hatası
- Database bağlantısını kontrol et
- `.env` dosyasında `DATABASE_URL` olduğunu doğrula

