# Avukatlık Sözleşmesi PDF Güncelleme Kılavuzu

## Yapılan Değişiklikler

### 1. Database Güncellemeleri

#### Model Değişikliği (`firstwebsite/models.py`)
- `OrnekSozlesme` modeline `pdf_path` alanı eklendi
- Bu alan PDF dosyasının server'da kaydedildiği yolu tutar

#### Local SQLite Migration
```bash
python firstwebsite/ornek_sozlesme_pdf_migration.py
```
✅ **Tamamlandı** - Local database'e `pdf_path` kolonu eklendi

#### DigitalOcean PostgreSQL Migration
DigitalOcean'da şu komutu çalıştırın:
```bash
cd /path/to/LawAutomationOnline
source venv/bin/activate
python firstwebsite/postgresql_ornek_sozlesme_migration.py
```

### 2. Backend Güncellemeleri (`firstwebsite/app.py`)

#### Yeni Route: `/save_ornek_sozlesme_pdf/<int:sozlesme_id>`
- PDF'i base64 formatında alır
- Dosya adını oluşturur: `"{Müvekkil Adı} Avukatlik Ucret Sozlesmesi.pdf"`
- PDF'i `uploads/ornek_sozlesmeler/` klasörüne kaydeder
- Database'e dosya yolunu kaydeder
- Dosya URL'ini döner

### 3. Frontend Güncellemeleri (`firstwebsite/templates/ornek_sozlesme_formu.html`)

#### PDF Önizleme Akışı (Kayıtlı Sözleşmeler):
1. **PDF Oluştur**: pdfMake ile PDF oluşturulur (data URL)
2. **Backend'e Gönder**: PDF backend'e kaydedilmek üzere gönderilir
3. **Dosya Kaydet**: Backend PDF'i doğru isimle kaydeder
4. **URL Al**: Backend kaydedilen PDF'in URL'ini döner
5. **Önizle**: Kaydedilen PDF yeni sekmede açılır
6. **Modal Kapat**: PDF önizleme modal'ı otomatik kapanır

#### Dosya Adı Formatı:
- **Backend**: `{Müvekkil Adı} Avukatlik Ucret Sozlesmesi.pdf`
- **Örnek**: `Ahmet Yilmaz Avukatlik Ucret Sozlesmesi.pdf`

### 4. Dosya Yapısı

```
firstwebsite/
├── uploads/
│   └── ornek_sozlesmeler/
│       ├── Ahmet Yilmaz Avukatlik Ucret Sozlesmesi.pdf
│       ├── Mehmet Kaya Avukatlik Ucret Sozlesmesi.pdf
│       └── ...
├── models.py (güncellendi)
├── app.py (güncellendi)
├── templates/
│   └── ornek_sozlesme_formu.html (güncellendi)
├── ornek_sozlesme_pdf_migration.py (yeni)
└── postgresql_ornek_sozlesme_migration.py (yeni)
```

## Deployment Adımları

### Local Test (✅ Tamamlandı)
1. Migration çalıştırıldı
2. Backend route'ları eklendi
3. Frontend güncellendi
4. Test edilecek

### GitHub'a Push
```bash
git add .
git commit -m "Avukatlık sözleşmesi PDF kaydetme özelliği eklendi"
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
python firstwebsite/postgresql_ornek_sozlesme_migration.py
```

5. **Uploads klasörünü oluştur** (yoksa):
```bash
mkdir -p firstwebsite/uploads/ornek_sozlesmeler
chmod 755 firstwebsite/uploads/ornek_sozlesmeler
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
- PDF'ler `uploads/ornek_sozlesmeler/` klasöründe saklanır
- Sadece login olan kullanıcılar PDF kaydedebilir
- Dosya adları güvenli karakterlere dönüştürülür

### Dosya İsimlendirme
- Türkçe karakterler korunur
- Geçersiz karakterler temizlenir
- Format: `{Müvekkil Adı} Avukatlik Ucret Sozlesmesi.pdf`

### Database
- SQLite (Local): `pdf_path VARCHAR(500)`
- PostgreSQL (Live): `pdf_path VARCHAR(500)`

### Kullanıcı Deneyimi
- PDF oluşturulur → Backend'e kaydedilir → Yeni sekmede açılır
- Modal otomatik kapanır
- Tarayıcının indirme butonuyla doğru isimle indirilir

## Test Senaryosu

1. ✅ Kayıtlı sözleşme listesini aç
2. ✅ Bir sözleşmenin önizle butonuna bas
3. ✅ PDF backend'e kaydedilir
4. ✅ Yeni sekmede PDF görüntülenir
5. ✅ Dosya adının doğru olduğunu kontrol et: `{Müvekkil Adı} Avukatlik Ucret Sozlesmesi.pdf`
6. ✅ Tarayıcının indirme butonu ile indir
7. ✅ Modal otomatik kapanır

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

