"""
E-posta gönderimi için temiz ve basit sistem
"""

import os
from dotenv import load_dotenv
import logging

# .env dosyasını yükle
load_dotenv()

# Logger ayarla
logger = logging.getLogger(__name__)

def send_email(to_email, subject, body, is_html=False):
    """
    E-posta gönder - SendGrid API kullanarak
    """
    try:
        # SendGrid API anahtarını al
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        from_email = os.getenv('MAIL_USERNAME', 'noreply@kaplanhukukotomasyon.com')

        if not sendgrid_api_key:
            logger.error("SENDGRID_API_KEY bulunamadi")
            return False, "SendGrid API anahtari bulunamadi"

        # SendGrid kütüphanesini import et
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
        except ImportError:
            logger.error("sendgrid kutuphanesi yuklu degil. 'pip install sendgrid' calistirin")
            return False, "SendGrid kutuphanesi yuklu degil"

        # E-posta içeriğini hazırla
        if is_html:
            content = Content("text/html", body)
        else:
            content = Content("text/plain", body)

        # Mail objesini oluştur
        mail = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=content if not is_html else None,
            html_content=content if is_html else None
        )

        # SendGrid client oluştur ve gönder
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(mail)

        logger.info(f"E-posta basariyla gonderildi: {to_email}, Status: {response.status_code}")
        return True, "E-posta basariyla gonderildi"

    except Exception as e:
        error_msg = f"E-posta gonderme hatasi: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False, error_msg

def send_test_email():
    """
    Test e-postasi gonder
    """
    test_email = os.getenv('MAIL_USERNAME')
    if not test_email:
        return False, "Test e-posta adresi bulunamadi"
    
    subject = "Test E-posta"
    body = """
    Bu bir test e-postasi.
    
    E-posta sistemi calisiyor.
    
    Kaplan Hukuk Otomasyon
    """
    
    return send_email(test_email, subject, body)

def send_notification_email(to_email, subject, body):
    """
    Bildirim e-postasi gonder
    """
    return send_email(to_email, subject, body, is_html=True)

def send_calendar_event_assignment_email(user_email, user_name, event_title, event_date, event_time, event_type, assigned_by_name, courthouse=None, department=None, description=None):
    """
    Takvim etkinliği atama bildirimi gönder
    """
    event_type_names = {
        'durusma': 'Duruşma',
        'e-durusma': 'E-Duruşma',
        'tahliye': 'Tahliye',
        'is': 'Yapılacak İş',
        'randevu': 'Randevu',
        'diger': 'Diğer'
    }
    
    event_type_display = event_type_names.get(event_type, event_type)
    
    subject = f"Yeni Etkinlik Ataması: {event_title}"
    
    body = f"""Merhaba {user_name},

Size yeni bir etkinlik atanmıştır:

📅 Etkinlik: {event_title}
📋 Türü: {event_type_display}
📅 Tarih: {event_date}
⏰ Saat: {event_time}"""

    # Duruşma/E-Duruşma dışındaki türlerde atayan bilgisini göster
    if event_type not in ['durusma', 'e-durusma'] and assigned_by_name:
        body += f"\n👤 Atayan: {assigned_by_name}"
    
    # Duruşma ve E-duruşma için adliye ve mahkeme bilgilerini ekle
    if event_type in ['durusma', 'e-durusma']:
        if courthouse:
            body += f"\n🏛️ Adliye: {courthouse}"
        if department:
            body += f"\n⚖️ Mahkeme/Birim: {department}"
    
    # Açıklama varsa en sona ekle
    if description and description.strip():
        body += f"\n\n📝 Açıklama:\n{description.strip()}"
    
    body += f"""

Lütfen bu etkinliği takip ediniz.

Hukuk Bürosu Yönetim Sistemi"""
    
    return send_email(user_email, subject, body.strip())

def send_calendar_event_reminder_email(user_email, user_name, event_title, event_date, event_time, event_type, courthouse=None, department=None, description=None):
    """
    Takvim etkinliği hatırlatma bildirimi gönder
    """
    event_type_names = {
        'durusma': 'Duruşma',
        'e-durusma': 'E-Duruşma',
        'tahliye': 'Tahliye',
        'is': 'Yapılacak İş',
        'randevu': 'Randevu',
        'diger': 'Diğer'
    }
    
    event_type_display = event_type_names.get(event_type, event_type)
    
    subject = f"Etkinlik Hatırlatması: {event_title}"
    
    body = f"""Merhaba {user_name},

Size atanan etkinlik yaklaşıyor:

📅 Etkinlik: {event_title}
📋 Türü: {event_type_display}
📅 Tarih: {event_date}
⏰ Saat: {event_time}"""
    
    # Duruşma ve E-duruşma için adliye ve mahkeme bilgilerini ekle
    if event_type in ['durusma', 'e-durusma']:
        if courthouse:
            body += f"\n🏛️ Adliye: {courthouse}"
        if department:
            body += f"\n⚖️ Mahkeme/Birim: {department}"
    
    # Açıklama varsa en sona ekle
    if description and description.strip():
        body += f"\n\n📝 Açıklama:\n{description.strip()}"
    
    body += f"""

Lütfen bu etkinliği unutmayınız.

Hukuk Bürosu Yönetim Sistemi"""
    
    return send_email(user_email, subject, body.strip())

if __name__ == "__main__":
    # Test e-postasi gonder
    print("Test e-postasi gonderiliyor...")
    success, message = send_test_email()
    
    if success:
        print(f"Basarili: {message}")
    else:
        print(f"Hata: {message}")