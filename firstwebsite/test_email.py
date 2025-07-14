# -*- coding: utf-8 -*-
"""
E-posta sistemini test etmek için basit script
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

import locale
try:
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
    except locale.Error:
        pass

from flask import Flask
from flask_mail import Mail, Message

# Flask app oluştur
app = Flask(__name__)

# E-posta konfigürasyonu
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_ASCII_ATTACHMENTS'] = False
app.config['MAIL_SUPPRESS_SEND'] = False
app.config['MAIL_DEBUG'] = False

# Mail nesnesini oluştur
mail = Mail(app)

def test_email_with_turkish_chars():
    """Türkçe karakterler içeren test e-postası gönder"""
    
    with app.app_context():
        try:
            # Test e-posta içeriği - Türkçe karakterler içeren
            subject = "Test E-posta - Türkçe Karakter Testi: üğıöçş ÜĞIÖÇŞ"
            
            body = """
            <html>
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">Türkçe Karakter Testi</h2>
                    <p>Bu e-posta Türkçe karakter desteğini test etmek için gönderilmiştir.</p>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3>Test Karakterleri:</h3>
                        <ul>
                            <li>Küçük harfler: ç, ğ, ı, ö, ş, ü</li>
                            <li>Büyük harfler: Ç, Ğ, I, Ö, Ş, Ü</li>
                            <li>Örnek kelimeler: Türkiye, İstanbul, Ankara, Müşteri, Güçlü</li>
                            <li>Örnek cümle: "Hükümet, güçlü bir şekilde ülkeyi yönetiyor."</li>
                        </ul>
                    </div>
                    
                    <p>Bu e-posta <strong>UTF-8 encoding</strong> ile gönderilmiştir.</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Test e-postası - Kaplan Hukuk Otomasyon
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Subject ve body'yi UTF-8 olarak encode et
            if isinstance(subject, str):
                subject = subject.encode('utf-8').decode('utf-8')
            if isinstance(body, str):
                body = body.encode('utf-8').decode('utf-8')
            
            # E-posta mesajını oluştur
            msg = Message(
                subject=subject,
                recipients=[app.config['MAIL_USERNAME']],  # Kendimize gönder
                html=body,
                sender=app.config['MAIL_DEFAULT_SENDER'],
                charset='utf-8'
            )
            
            # Message header'larını UTF-8 olarak ayarla
            msg.extra_headers = {'Content-Type': 'text/html; charset=utf-8'}
            
            # E-postayı gönder
            mail.send(msg)
            
            print("✅ Test e-postası başarıyla gönderildi!")
            print(f"📧 Gönderilen adres: {app.config['MAIL_USERNAME']}")
            print(f"📝 Konu: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ E-posta gönderme hatası: {e}")
            print(f"📋 Hata türü: {type(e).__name__}")
            return False

def test_simple_email():
    """Basit test e-postası gönder"""
    
    with app.app_context():
        try:
            # Basit e-posta
            subject = "Test E-posta - Basit Test"
            body = "Bu basit bir test e-postasıdır."
            
            msg = Message(
                subject=subject,
                recipients=[app.config['MAIL_USERNAME']],
                body=body,
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            
            mail.send(msg)
            print("✅ Basit test e-postası başarıyla gönderildi!")
            return True
            
        except Exception as e:
            print(f"❌ Basit e-posta gönderme hatası: {e}")
            return False

def check_email_config():
    """E-posta konfigürasyonunu kontrol et"""
    print("🔧 E-posta konfigürasyonu kontrol ediliyor...")
    
    config_items = [
        ('MAIL_USERNAME', app.config.get('MAIL_USERNAME')),
        ('MAIL_PASSWORD', '***' if app.config.get('MAIL_PASSWORD') else None),
        ('MAIL_SERVER', app.config.get('MAIL_SERVER')),
        ('MAIL_PORT', app.config.get('MAIL_PORT')),
        ('MAIL_USE_TLS', app.config.get('MAIL_USE_TLS')),
        ('MAIL_DEFAULT_SENDER', app.config.get('MAIL_DEFAULT_SENDER')),
    ]
    
    for key, value in config_items:
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")
    
    missing_config = [key for key, value in config_items if not value]
    if missing_config:
        print(f"\n❌ Eksik konfigürasyon: {', '.join(missing_config)}")
        return False
    
    print("\n✅ E-posta konfigürasyonu tamamlanmış!")
    return True

if __name__ == '__main__':
    print("🚀 E-posta sistemi test başlıyor...\n")
    
    # Konfigürasyonu kontrol et
    if not check_email_config():
        print("\n❌ E-posta konfigürasyonu tamamlanmamış. .env dosyasını kontrol edin.")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("📧 E-posta testleri başlıyor...")
    print("="*50)
    
    # Test 1: Basit e-posta
    print("\n1️⃣ Basit e-posta testi:")
    test_simple_email()
    
    # Test 2: Türkçe karakter testi
    print("\n2️⃣ Türkçe karakter testi:")
    test_email_with_turkish_chars()
    
    print("\n" + "="*50)
    print("✅ E-posta testleri tamamlandı!")
    print("📬 E-posta kutunuzu kontrol edin.")
    print("="*50)