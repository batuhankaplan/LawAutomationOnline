"""
E-posta gönderimi için temiz ve basit sistem
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging

# .env dosyasını yükle
load_dotenv()

# Logger ayarla
logger = logging.getLogger(__name__)

def send_email(to_email, subject, body, is_html=False):
    """
    E-posta gönder - Gmail SMTP kullanarak
    """
    try:
        # Environment variables'daki Türkçe karakterleri temizle
        env_vars_to_clean = ['COMPUTERNAME', 'HOSTNAME', 'LOGONSERVER', 'USERDOMAIN', 'USERDOMAIN_ROAMINGPROFILE']
        for var in env_vars_to_clean:
            if var in os.environ:
                # Türkçe karakterleri ASCII safe karakterlerle değiştir
                safe_value = os.environ[var]
                # Türkçe karakterleri değiştir
                safe_value = safe_value.replace('ü', 'u').replace('Ü', 'U')
                safe_value = safe_value.replace('ç', 'c').replace('Ç', 'C')
                safe_value = safe_value.replace('ğ', 'g').replace('Ğ', 'G')
                safe_value = safe_value.replace('ı', 'i').replace('İ', 'I')
                safe_value = safe_value.replace('ö', 'o').replace('Ö', 'O')
                safe_value = safe_value.replace('ş', 's').replace('Ş', 'S')
                # Genel Unicode karakterleri için encode/decode
                try:
                    safe_value = safe_value.encode('ascii', 'ignore').decode('ascii')
                except:
                    safe_value = "CLEAN_VALUE"
                os.environ[var] = safe_value
        # Gmail SMTP ayarları
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Kimlik bilgileri
        from_email = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')
        
        if not from_email or not password:
            logger.error("E-posta kimlik bilgileri bulunamadi")
            return False, "E-posta kimlik bilgileri bulunamadi"
        
        # E-posta mesajini olustur
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # İçerik türünü belirle
        if is_html:
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # SMTP baglantisi kur ve e-posta gonder
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Hostname'i manuel olarak temiz bir değerle ayarla
            server.local_hostname = "localhost"
            server.starttls(context=context)
            server.login(from_email, password)
            server.send_message(msg)
        
        logger.info(f"E-posta basariyla gonderildi: {to_email}")
        return True, "E-posta basariyla gonderildi"
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP kimlik dogrulama hatasi: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except smtplib.SMTPException as e:
        error_msg = f"SMTP hatasi: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"E-posta gonderme hatasi: {str(e)}"
        logger.error(error_msg)
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
⏰ Saat: {event_time}
👤 Atayan: {assigned_by_name}"""
    
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