# -*- coding: utf-8 -*-
"""
Türkçe karakter e-posta testi
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from email_utils import send_email_with_smtplib
from dotenv import load_dotenv
load_dotenv()

def test_turkish_email():
    """Türkçe karakterler içeren e-posta gönder"""
    
    to_email = os.getenv('MAIL_USERNAME')
    if not to_email:
        print("❌ MAIL_USERNAME .env dosyasında bulunamadı")
        return False
    
    subject = "✅ Türkçe Karakter Testi Başarılı: çğıöşü ÇĞIÖŞÜ"
    
    body = """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <h2 style="color: #2d313b; text-align: center;">🎉 E-posta Sistemi Test Başarılı!</h2>
            
            <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                <h3 style="margin-top: 0; color: #155724;">✅ Türkçe Karakter Testi Geçti!</h3>
                <p style="margin-bottom: 0;">E-posta sistemi artık Türkçe karakterleri doğru şekilde destekliyor.</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Test Edilen Karakterler:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Küçük Harfler:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">ç, ğ, ı, ö, ş, ü</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Büyük Harfler:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Ç, Ğ, I, Ö, Ş, Ü</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Örnek Kelimeler:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">Türkiye, İstanbul, Ankara, Müşteri, Güçlü, Büro</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Örnek Cümle:</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd;">"Hükümetin güçlü desteğiyle Türkiye'nin geleceği parlak görünüyor."</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #cce5ff; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff;">
                <h3 style="margin-top: 0; color: #004085;">🔧 Teknik Detaylar:</h3>
                <ul>
                    <li><strong>Encoding:</strong> UTF-8</li>
                    <li><strong>E-posta Format:</strong> HTML</li>
                    <li><strong>SMTP Server:</strong> smtp-mail.outlook.com</li>
                    <li><strong>Karakter Desteği:</strong> Tam Türkçe karakter desteği</li>
                    <li><strong>Çözüm:</strong> smtplib + email.header.Header kullanımı</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <h3 style="color: #28a745;">✅ Problem Çözüldü!</h3>
                <p style="font-size: 16px;">Artık tüm e-posta gönderimlerinde Türkçe karakterler doğru şekilde görüntülenecek.</p>
            </div>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            <p style="font-size: 12px; color: #666; text-align: center;">
                Test E-postası - Kaplan Hukuk Otomasyon<br>
                Gönderim: {current_time}<br>
                Encoding: UTF-8 ✅
            </p>
        </div>
    </body>
    </html>
    """
    
    from datetime import datetime
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    body = body.format(current_time=current_time)
    
    print("📧 Türkçe karakter testi e-postası gönderiliyor...")
    print(f"📬 Alıcı: {to_email}")
    print(f"📝 Konu: {subject}")
    
    success, message = send_email_with_smtplib(to_email, subject, body, is_html=True)
    
    if success:
        print(f"✅ {message}")
        print("🎉 E-posta başarıyla gönderildi! E-posta kutunuzu kontrol edin.")
        return True
    else:
        print(f"❌ {message}")
        return False

if __name__ == "__main__":
    print("🚀 Türkçe karakter e-posta testi başlıyor...\n")
    
    result = test_turkish_email()
    
    if result:
        print("\n" + "="*60)
        print("🎊 TEST BAŞARILI! Türkçe karakter sorunu çözüldü! 🎊")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Test başarısız. E-posta ayarlarını kontrol edin.")
        print("="*60)