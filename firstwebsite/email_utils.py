# -*- coding: utf-8 -*-
"""
E-posta gönderimi için yardımcı fonksiyonlar
Türkçe karakter desteği ve modern auth desteği ile
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv
import logging

# .env dosyasını yükle
load_dotenv()

# Logger ayarla
logger = logging.getLogger(__name__)

def send_email_with_smtplib(to_email, subject, body, is_html=True):
    """
    smtplib kullanarak e-posta gönder
    Türkçe karakter desteği ile
    """
    try:
        # E-posta ayarları - Gmail kullan
        smtp_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_PORT', 587))
        from_email = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')
        
        if not from_email or not password:
            return False, "E-posta bilgileri .env dosyasında bulunamadı"
        
        # E-posta mesajını oluştur
        message = MIMEMultipart("alternative")
        
        # Türkçe karakter desteği için subject encoding
        from email.header import Header
        subject_encoded = Header(subject.encode('utf-8'), 'utf-8').encode()
        message["Subject"] = subject_encoded
        message["From"] = from_email
        message["To"] = to_email
        
        # Türkçe karakter desteği için encoding
        message.set_charset('utf-8')
        
        # Body'yi ekle
        if is_html:
            body_part = MIMEText(body, "html", "utf-8")
        else:
            body_part = MIMEText(body, "plain", "utf-8")
            
        message.attach(body_part)
        
        # SMTP sunucusuna bağlan ve e-posta gönder
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(from_email, password)
            
            # E-postayı gönder - UTF-8 encoding ile
            text = message.as_string()
            server.sendmail(from_email, to_email, text.encode('utf-8'))
        
        logger.info(f"E-posta başarıyla gönderildi: {to_email}")
        return True, "E-posta başarıyla gönderildi"
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP kimlik doğrulama hatası: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except smtplib.SMTPException as e:
        error_msg = f"SMTP hatası: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"E-posta gönderme hatası: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_gmail_email(to_email, subject, body, is_html=True):
    """
    Gmail SMTP kullanarak e-posta gönder
    """
    try:
        # Gmail ayarları
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        from_email = os.getenv('GMAIL_USERNAME')  # Gmail adresi
        password = os.getenv('GMAIL_APP_PASSWORD')  # Gmail app password
        
        if not from_email or not password:
            return False, "Gmail bilgileri .env dosyasında bulunamadı"
        
        # E-posta mesajını oluştur
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email
        
        # Türkçe karakter desteği için encoding
        message.set_charset('utf-8')
        
        # Body'yi ekle
        if is_html:
            body_part = MIMEText(body, "html", "utf-8")
        else:
            body_part = MIMEText(body, "plain", "utf-8")
            
        message.attach(body_part)
        
        # Gmail SMTP sunucusuna bağlan
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(from_email, password)
            
            # E-postayı gönder
            text = message.as_string()
            server.sendmail(from_email, to_email, text.encode('utf-8'))
        
        logger.info(f"Gmail üzerinden e-posta gönderildi: {to_email}")
        return True, "Gmail üzerinden e-posta başarıyla gönderildi"
        
    except Exception as e:
        error_msg = f"Gmail e-posta gönderme hatası: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_test_email():
    """
    Test e-postası gönder
    """
    test_email = os.getenv('MAIL_USERNAME')
    if not test_email:
        return False, "Test e-posta adresi bulunamadı"
    
    subject = "Test E-posta - Türkçe Karakter Testi: üğıöçş ÜĞIÖÇŞ"
    
    body = """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c5aa0;">✅ E-posta Sistemi Test Başarılı!</h2>
            <p>Bu e-posta Türkçe karakter desteğini test etmek için gönderilmiştir.</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Test Edilen Karakterler:</h3>
                <ul>
                    <li><strong>Küçük harfler:</strong> ç, ğ, ı, ö, ş, ü</li>
                    <li><strong>Büyük harfler:</strong> Ç, Ğ, I, Ö, Ş, Ü</li>
                    <li><strong>Örnek kelimeler:</strong> Türkiye, İstanbul, Ankara, Müşteri, Güçlü</li>
                    <li><strong>Örnek cümle:</strong> "Hükümet, güçlü bir şekilde ülkeyi yönetiyor."</li>
                </ul>
            </div>
            
            <div style="background: #d4edda; padding: 10px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 0; color: #155724;">
                    <strong>✅ Başarılı!</strong> E-posta sistemi Türkçe karakterleri doğru şekilde destekliyor.
                </p>
            </div>
            
            <p>Bu e-posta <strong>UTF-8 encoding</strong> ile gönderilmiştir.</p>
            
            <hr style="margin: 30px 0;">
            <p style="font-size: 12px; color: #666;">
                Test e-postası - Kaplan Hukuk Otomasyon<br>
                Encoding: UTF-8<br>
                Gönderim Zamanı: {current_time}
            </p>
        </div>
    </body>
    </html>
    """
    
    from datetime import datetime
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    body = body.format(current_time=current_time)
    
    return send_email_with_smtplib(test_email, subject, body, is_html=True)

if __name__ == "__main__":
    print("🚀 E-posta utility test başlıyor...")
    
    # Test e-postası gönder
    success, message = send_test_email()
    
    if success:
        print(f"✅ {message}")
        print(f"📧 Test e-postası gönderildi: {os.getenv('MAIL_USERNAME')}")
    else:
        print(f"❌ {message}")
        
        # Gmail alternatifini dene
        print("\n🔄 Gmail alternatifi deneniyor...")
        success, message = send_gmail_email(
            os.getenv('MAIL_USERNAME'),
            "Gmail Test",
            "Gmail test e-postası"
        )
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")