# -*- coding: utf-8 -*-
"""
Basit e-posta testi - sadece bağlantıyı test et
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import os
from dotenv import load_dotenv

load_dotenv()

def test_smtp_connection():
    """SMTP bağlantısını test et"""
    
    smtp_server = "smtp-mail.outlook.com"
    smtp_port = 587
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    print(f"🔧 SMTP Test Başlıyor...")
    print(f"📧 E-posta: {username}")
    print(f"🔑 Şifre: {'*' * len(password) if password else 'YOK'}")
    print(f"🌐 Sunucu: {smtp_server}:{smtp_port}")
    
    try:
        # SMTP bağlantısını oluştur
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("🔗 SMTP sunucusuna bağlanıyor...")
            server.set_debuglevel(1)  # Debug modu
            
            print("🔐 TLS başlatılıyor...")
            server.starttls(context=context)
            
            print("👤 Giriş yapılıyor...")
            server.login(username, password)
            
            print("✅ SMTP bağlantısı başarılı!")
            
            # Basit e-posta gönder
            msg = MIMEMultipart()
            msg["From"] = username
            msg["To"] = username
            msg["Subject"] = Header("Test - Basit Bağlantı", "utf-8").encode()
            
            body = "Bu basit bir bağlantı testidir."
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            print("📤 E-posta gönderiliyor...")
            server.sendmail(username, username, msg.as_string())
            print("✅ E-posta başarıyla gönderildi!")
            
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Kimlik doğrulama hatası: {e}")
        return False
    except Exception as e:
        print(f"❌ Genel hata: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SMTP Bağlantı Testi\n")
    
    success = test_smtp_connection()
    
    if success:
        print("\n🎉 Test başarılı!")
    else:
        print("\n❌ Test başarısız!")