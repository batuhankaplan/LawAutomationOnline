# Kaplan Hukuk Otomasyon Sistemi

Avukat ofisleri için geliştirilmiş kapsamlı hukuk otomasyon yazılımı.

## Özellikler

- 👥 **Kullanıcı Yönetimi**: Rol tabanlı yetkilendirme sistemi
- 📁 **Dosya Yönetimi**: Dava dosyaları ve belge yönetimi
- 📅 **Takvim Sistemi**: Duruşma ve etkinlik takibi
- 💰 **Finansal Yönetim**: Ödeme takibi ve masraf yönetimi
- 🤖 **AI Asistan**: Gemini AI ile hukuki destek
- 📊 **Raporlama**: Detaylı istatistikler ve raporlar
- 📧 **E-posta Entegrasyonu**: Otomatik bildirimler
- 🔒 **Güvenlik**: 2FA, CSRF koruması ve şifreleme

## Kurulum

### Gereksinimler
- Python 3.8+
- SQLite3
- Modern web tarayıcısı

### Adım 1: Bağımlılıkları Yükle
```bash
pip install -r requirements.txt
```

### Adım 2: Environment Ayarları
`.env` dosyasını kendi ayarlarınızla güncelleyin:
```env
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
SECRET_KEY=your-secure-secret-key
DEBUG=False
HOST=0.0.0.0
PORT=5000
```

### Adım 3: Uygulamayı Başlat
```bash
python start_app.py
```

## Production Dağıtımı

### Nginx Konfigürasyonu
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd Servisi
```ini
[Unit]
Description=Kaplan Hukuk Otomasyon
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/usr/bin/python3 start_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Güvenlik Önlemleri

- ✅ DEBUG=False (production için)
- ✅ Güçlü SECRET_KEY kullanımı
- ✅ CSRF Token koruması
- ✅ SQL Injection koruması
- ✅ XSS koruması
- ✅ 2FA desteği

## Veritabanı Yönetimi

### Yedekleme
Sistem üzerinden "Veritabanı Yönetimi" sayfasından yedekleme alabilirsiniz.

### Temizleme
**DİKKAT**: "Veritabanı Temizle" özelliği tüm verileri siler. Önce yedekleme alın!

## Destek

Bu yazılım tamamen kullanıma hazır durumda olup, production ortamında güvenle kullanılabilir.

---

**© 2024 Kaplan Hukuk - Tüm hakları saklıdır.**