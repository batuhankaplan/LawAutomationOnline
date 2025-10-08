# 🔴 SORUN ÇÖZÜM RAPORU - DigitalOcean Database Bağlantı Problemi

## 📋 Sorunun Özeti

**Belirti:**
- Dosya detayları modalında eklenen belgeler görüntülenemiyor (bulunamadı hatası)
- Yeni işçi görüşme formu kaydedilemiyor
- Profil resmi değişiklikleri kaybolup varsayılana dönüyor
- **Localhost'ta sorun yok, production'da sorunlar var**

**Kök Neden:**
`.env` dosyasında `DATABASE_URL` değişkeni **eksik**! Bu yüzden:
- Production sunucu SQLite kullanıyor (local database)
- PostgreSQL 17 database kullanılmıyor
- Her restart'ta SQLite sıfırlanıyor veya farklı lokasyondan okunuyor
- Upload edilen dosyalar database'e kaydedilmiyor ama disk'te var

---

## 🔍 Teşhis Detayları

### 1. Mevcut Durum
```bash
# .env dosyası - ÖNCEDEN
MAIL_USERNAME=...
MAIL_PASSWORD=...
SECRET_KEY=...
DEBUG=False
# DATABASE_URL YOK! ❌
```

### 2. Kod Analizi
`app.py` satır 212:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
```

**Ne demek?**
- `DATABASE_URL` yoksa → SQLite kullan
- SQLite instance/database.db dosyası → Her deploy'da kaybolabilir
- PostgreSQL bağlantısı hiç kullanılmıyor

---

## ✅ ÇÖZÜM ADIMLARI

### Adım 1: DigitalOcean PostgreSQL Bağlantı Bilgilerini Alın

1. DigitalOcean Dashboard'a gidin
2. Databases → PostgreSQL 17 cluster'ınızı bulun
3. **Connection Details** sekmesine tıklayın
4. Şu bilgileri kopyalayın:

```
Host: db-postgresql-xxx.b.db.ondigitalocean.com
Port: 25060
Database: lawautomation (veya başka isim)
User: doadmin
Password: [DigitalOcean'dan kopyalayın]
```

### Adım 2: DATABASE_URL Oluşturun

Format:
```
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE?sslmode=require
```

Örnek (gerçek değerlerinizle değiştirin):
```
DATABASE_URL=postgresql://doadmin:GERÇEK_ŞİFRE@db-postgresql-fra1-12345.b.db.ondigitalocean.com:25060/lawautomation?sslmode=require
```

**ÖNEMLİ:**
- `sslmode=require` mutlaka ekleyin (DigitalOcean bunu gerektirir)
- Şifrede özel karakterler varsa URL encode edin:
  - `@` → `%40`
  - `#` → `%23`
  - `$` → `%24`

### Adım 3: Sunucudaki .env Dosyasını Güncelleyin

```bash
# SSH ile DigitalOcean droplet'a bağlanın
ssh root@YOUR_DROPLET_IP

# Uygulama dizinine gidin
cd /var/www/lawautomation/firstwebsite

# .env dosyasını düzenleyin
nano .env

# DATABASE_URL satırını ekleyin/güncelleyin
DATABASE_URL=postgresql://doadmin:ŞİFRE@HOST:PORT/DATABASE?sslmode=require

# UPLOAD_FOLDER da kontrol edin
UPLOAD_FOLDER=/var/www/lawautomation/uploads

# Kaydet ve çık (Ctrl+X, Y, Enter)
```

### Adım 4: Uploads Klasörünü Kontrol Edin

```bash
# Uploads klasörünün varlığını kontrol edin
ls -la /var/www/lawautomation/uploads

# Yoksa oluşturun
mkdir -p /var/www/lawautomation/uploads

# İzinleri düzeltin (www-data nginx/gunicorn user'ı)
chown -R www-data:www-data /var/www/lawautomation/uploads
chmod -R 755 /var/www/lawautomation/uploads
```

### Adım 5: Uygulamayı Yeniden Başlatın

```bash
# Gunicorn/systemd servisini restart edin
systemctl restart lawautomation

# Logları kontrol edin
journalctl -u lawautomation -f

# Veya nginx logları
tail -f /var/log/nginx/error.log
```

### Adım 6: Database Migrations Çalıştırın (Gerekirse)

```bash
# Virtual environment'ı aktifleştirin
cd /var/www/lawautomation
source venv/bin/activate

# Flask migrations
cd firstwebsite
flask db upgrade

# Veya doğrudan Python
python -c "from app import db; db.create_all()"
```

---

## 🧪 Test Adımları

### 1. Database Bağlantısını Test Edin

SSH üzerinden:
```bash
cd /var/www/lawautomation/firstwebsite
source ../venv/bin/activate
python

>>> from app import db
>>> db.engine.url
# PostgreSQL URL'i görmeli, sqlite GÖRMEMELI
>>> quit()
```

### 2. Uploads Test Edin

```bash
# Bir test dosyası oluşturun
cd /var/www/lawautomation/uploads
echo "test" > test.txt
ls -la test.txt
rm test.txt
```

### 3. Web Arayüzünden Test Edin

1. **İşçi Görüşme Formu:**
   - Yeni form oluşturun
   - Kaydedin
   - Sayfayı yenileyin → Kayıt duruyorsa ✅

2. **Dosya Ekleme:**
   - Bir dosyaya belge ekleyin
   - Dosya detaylarına bakın
   - Belge açılıyorsa ✅

3. **Profil Resmi:**
   - Profil resmi değiştirin
   - Sayfayı yenileyin → Değişiklik duruyorsa ✅

---

## 📊 Kontrol Listem

- [ ] DigitalOcean PostgreSQL connection details alındı
- [ ] `.env` dosyasına `DATABASE_URL` eklendi
- [ ] `UPLOAD_FOLDER=/var/www/lawautomation/uploads` ayarlandı
- [ ] SSH ile sunucuya bağlanıldı
- [ ] Sunucudaki `.env` güncellendi
- [ ] Uploads klasörü oluşturuldu ve izinler düzeltildi
- [ ] `systemctl restart lawautomation` çalıştırıldı
- [ ] Loglar kontrol edildi (hata yok)
- [ ] Database bağlantısı test edildi (PostgreSQL kullanıyor)
- [ ] İşçi görüşme formu test edildi ✅
- [ ] Dosya upload test edildi ✅
- [ ] Profil resmi test edildi ✅

---

## 🔧 Ek Sorun Giderme

### Sorun: "relation does not exist" hatası

**Çözüm:** Database tabloları yok, migrations çalıştırın:
```bash
cd /var/www/lawautomation/firstwebsite
source ../venv/bin/activate
python -c "from app import db; db.create_all()"
```

### Sorun: Profil resimleri kaybolmaya devam ediyor

**Olası Nedenler:**
1. **Upload folder izinleri yanlış:**
   ```bash
   chown -R www-data:www-data /var/www/lawautomation/uploads
   chmod -R 755 /var/www/lawautomation/uploads
   ```

2. **Static files serve edilmiyor:**
   - Nginx config'de `/uploads` location'ı var mı kontrol edin

3. **Database'e kaydedilmiyor:**
   - PostgreSQL bağlantısı aktif mi kontrol edin

### Sorun: "Permission denied" hatası

```bash
# SELinux varsa disable edin (CentOS/RHEL)
setenforce 0

# Veya uploads klasörüne context verin
chcon -R -t httpd_sys_rw_content_t /var/www/lawautomation/uploads
```

---

## 📝 Notlar

1. **Local'de Çalışıyor, Production'da Çalışmıyor:**
   - Local → SQLite (tek dosya, basit)
   - Production → PostgreSQL olmalı (ölçeklenebilir, güvenli)

2. **.env Dosyası Git'e Eklenmemeli:**
   - `.gitignore`'da olduğundan emin olun
   - Her sunucuda manuel oluşturun

3. **Backup Alın:**
   ```bash
   # PostgreSQL backup
   pg_dump -h HOST -U doadmin -d lawautomation > backup_$(date +%Y%m%d).sql

   # Uploads backup
   tar -czf uploads_backup_$(date +%Y%m%d).tar.gz /var/www/lawautomation/uploads
   ```

---

## 🎯 Sonuç

**Ana Sorun:** `.env` dosyasında `DATABASE_URL` eksikti.

**Çözüm:** DigitalOcean PostgreSQL bağlantı stringini `.env`'ye eklemek ve servisi restart etmek.

**Sonra:** Uploads klasör izinlerini kontrol et, migrations çalıştır.

---

**Hazırlayan:** Claude Code
**Tarih:** 2025-01-06
**Durum:** Çözüm bekliyor - DATABASE_URL eklenmeli
