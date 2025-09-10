# LawAutomation Deployment Kılavuzu

## 🚀 Hızlı Başlangıç

Bu kılavuz, LawAutomation uygulamasını production ortamına deploy etmek için gereken tüm adımları içerir.

## 📋 Gereksinimler

### Sunucu Gereksinimleri
- Ubuntu 22.04 LTS veya üzeri
- Minimum 2GB RAM
- 20GB+ disk alanı
- Python 3.11+

### Hizmet Sağlayıcılar
- **DigitalOcean** (Önerilen)
  - Droplet: Basic veya General Purpose
  - Managed Database: PostgreSQL (opsiyonel)
- Domain adı
- SSL sertifikası (Let's Encrypt ücretsiz)

## 🔧 Kurulum Adımları

### 1. Sunucu Hazırlığı

#### DigitalOcean'da Droplet Oluşturma
1. DigitalOcean hesabınıza giriş yapın
2. "Create Droplet" tıklayın
3. Ubuntu 22.04 LTS seçin
4. Plan seçin (Basic $12/ay yeterli)
5. Datacenter seçin (Frankfurt veya Amsterdam önerilir)
6. SSH key ekleyin veya password kullanın
7. Droplet'i oluşturun

#### Sunucuya Bağlanma
```bash
ssh root@your-server-ip
```

### 2. Otomatik Kurulum (Önerilen)

Deployment scriptini kullanarak otomatik kurulum:

```bash
# Dosyaları sunucuya kopyala
scp -r ./* root@your-server-ip:/var/www/lawautomation/

# Sunucuya bağlan
ssh root@your-server-ip

# Deploy scriptini çalıştır
cd /var/www/lawautomation
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

### 3. Manuel Kurulum

#### Sistem Paketlerini Güncelle
```bash
apt update && apt upgrade -y
```

#### Gerekli Paketleri Yükle
```bash
apt install -y python3.11 python3.11-venv python3-pip nginx postgresql postgresql-contrib git supervisor certbot python3-certbot-nginx
```

#### PostgreSQL Kurulumu
```bash
# PostgreSQL kullanıcı ve veritabanı oluştur
sudo -u postgres psql

CREATE USER lawautomation WITH PASSWORD 'güvenli-şifre';
CREATE DATABASE lawautomation OWNER lawautomation;
GRANT ALL PRIVILEGES ON DATABASE lawautomation TO lawautomation;
\q
```

#### Uygulama Dosyalarını Kopyala
```bash
# Dizin oluştur
mkdir -p /var/www/lawautomation
cd /var/www/lawautomation

# Dosyaları kopyala (lokalden)
# Veya Git'ten clone et
```

#### Python Ortamını Hazırla
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2-binary gunicorn
```

#### Environment Dosyası Oluştur
```bash
nano /var/www/lawautomation/.env
```

İçeriği:
```env
FLASK_ENV=production
SECRET_KEY=çok-güvenli-rastgele-bir-anahtar-min-32-karakter
DATABASE_URL=postgresql://lawautomation:şifre@localhost/lawautomation
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
UPLOAD_FOLDER=/var/www/lawautomation/uploads/
```

#### Veritabanını Başlat
```bash
cd /var/www/lawautomation/firstwebsite
source ../venv/bin/activate
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 4. Gunicorn Yapılandırması

Gunicorn config dosyası zaten hazır: `gunicorn_config.py`

### 5. Systemd Service Kurulumu

```bash
# Service dosyasını kopyala
cp deployment/lawautomation.service /etc/systemd/system/

# Service'i etkinleştir ve başlat
systemctl daemon-reload
systemctl enable lawautomation
systemctl start lawautomation

# Durumu kontrol et
systemctl status lawautomation
```

### 6. Nginx Yapılandırması

```bash
# Nginx config'i kopyala
cp deployment/nginx.conf /etc/nginx/sites-available/lawautomation

# Domain adını güncelle
nano /etc/nginx/sites-available/lawautomation
# yourdomain.com'u kendi domaininizle değiştirin

# Site'i etkinleştir
ln -s /etc/nginx/sites-available/lawautomation /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Nginx'i test et ve yeniden başlat
nginx -t
systemctl restart nginx
```

### 7. SSL Sertifikası (Let's Encrypt)

```bash
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 8. Firewall Ayarları

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 🔍 Test ve Doğrulama

### Sağlık Kontrolü
```bash
curl https://yourdomain.com/health
```

### Log Kontrolü
```bash
# Uygulama logları
journalctl -u lawautomation -f

# Nginx logları
tail -f /var/log/nginx/lawautomation_access.log
tail -f /var/log/nginx/lawautomation_error.log

# Gunicorn logları
tail -f /var/log/lawautomation/gunicorn_access.log
tail -f /var/log/lawautomation/gunicorn_error.log
```

## 🔐 Güvenlik Kontrol Listesi

- [ ] SECRET_KEY değiştirildi
- [ ] Veritabanı şifresi güçlü
- [ ] Admin şifresi değiştirildi
- [ ] SSL sertifikası aktif
- [ ] Firewall yapılandırıldı
- [ ] Dosya izinleri doğru (www-data:www-data)
- [ ] Debug modu kapalı
- [ ] Email ayarları yapılandırıldı

## 🔄 Güncelleme Prosedürü

```bash
# Sunucuya bağlan
ssh root@your-server-ip

# Uygulama dizinine git
cd /var/www/lawautomation

# Yedek al
cp -r firstwebsite firstwebsite.backup.$(date +%Y%m%d)
pg_dump lawautomation > backup_$(date +%Y%m%d).sql

# Güncellemeleri çek
git pull  # veya dosyaları manuel kopyala

# Bağımlılıkları güncelle
source venv/bin/activate
pip install -r requirements.txt

# Veritabanı migration (gerekirse)
cd firstwebsite
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Servisleri yeniden başlat
systemctl restart lawautomation
systemctl restart nginx
```

## 🆘 Sorun Giderme

### Uygulama başlamıyor
```bash
# Service durumunu kontrol et
systemctl status lawautomation

# Detaylı logları incele
journalctl -u lawautomation -n 100
```

### 502 Bad Gateway hatası
```bash
# Gunicorn çalışıyor mu kontrol et
ps aux | grep gunicorn

# Port dinleniyor mu kontrol et
netstat -tlnp | grep 8000
```

### Veritabanı bağlantı hatası
```bash
# PostgreSQL çalışıyor mu
systemctl status postgresql

# Bağlantıyı test et
sudo -u postgres psql -d lawautomation
```

### İzin hataları
```bash
# Dosya sahipliklerini düzelt
chown -R www-data:www-data /var/www/lawautomation
chmod -R 755 /var/www/lawautomation
chmod 600 /var/www/lawautomation/.env
```

## 📞 Destek

Sorun yaşarsanız:
1. Logları kontrol edin
2. Bu kılavuzdaki sorun giderme adımlarını uygulayın
3. GitHub'da issue açın

## 📝 Notlar

- İlk kurulumdan sonra admin şifresini hemen değiştirin
- Düzenli yedekleme yapın
- SSL sertifikasının otomatik yenilenmesini kontrol edin
- Sistem güncellemelerini düzenli yapın

---

**Başarılı bir deployment için tebrikler! 🎉**
