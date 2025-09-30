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
        'diger': 'Diğer',
        'arabuluculuk-toplantisi': 'Arabuluculuk Toplantısı',
        'gunluk-kayit': 'Günlük Kayıt'
    }

    event_type_icons = {
        'durusma': '⚖️',
        'e-durusma': '💻',
        'tahliye': '🏠',
        'is': '📋',
        'randevu': '👥',
        'diger': '📌',
        'arabuluculuk-toplantisi': '🤝',
        'gunluk-kayit': '📝'
    }

    event_type_display = event_type_names.get(event_type, event_type)
    event_icon = event_type_icons.get(event_type, '📌')

    subject = f"Yeni Etkinlik Ataması: {event_title}"

    # Ek bilgiler için HTML satırları
    extra_info_html = ""

    if event_type not in ['durusma', 'e-durusma'] and assigned_by_name:
        extra_info_html += f"""
        <tr>
            <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                <strong style="color: #495057;">👤 Atayan:</strong>
            </td>
            <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                {assigned_by_name}
            </td>
        </tr>"""

    if event_type in ['durusma', 'e-durusma']:
        if courthouse:
            extra_info_html += f"""
            <tr>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                    <strong style="color: #495057;">🏛️ Adliye:</strong>
                </td>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                    {courthouse}
                </td>
            </tr>"""
        if department:
            extra_info_html += f"""
            <tr>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                    <strong style="color: #495057;">⚖️ Mahkeme/Birim:</strong>
                </td>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                    {department}
                </td>
            </tr>"""

    description_html = ""
    if description and description.strip():
        description_html = f"""
        <div style="background-color: #f8f9fa; border-left: 4px solid #1e3c72; padding: 20px; border-radius: 4px; margin-top: 30px;">
            <p style="color: #495057; font-size: 14px; margin: 0 0 10px 0;">
                <strong>📝 Açıklama:</strong>
            </p>
            <p style="color: #212529; font-size: 14px; margin: 0; line-height: 1.6;">
                {description.strip()}
            </p>
        </div>"""

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 12px; overflow: hidden;">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px 30px; text-align: center;">
                                <img src="https://www.kaplanhukukotomasyon.com/static/images/logo.png" alt="Kaplan Hukuk Otomasyonu" style="max-width: 180px; height: auto; margin-bottom: 20px;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">{event_icon} Yeni Etkinlik Ataması</h1>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <p style="color: #333333; font-size: 16px; margin: 0 0 25px 0;">
                                    Merhaba <strong style="color: #1e3c72;">{user_name}</strong>,
                                </p>
                                <p style="color: #555555; font-size: 15px; margin: 0 0 30px 0;">
                                    Size yeni bir etkinlik atanmıştır:
                                </p>

                                <!-- Event Details Table -->
                                <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; margin-bottom: 20px;">
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; background-color: #f8f9fa;">
                                            <strong style="color: #495057;">📅 Etkinlik:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; background-color: #f8f9fa; color: #1e3c72; font-weight: 600;">
                                            {event_title}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                                            <strong style="color: #495057;">📋 Türü:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                                            {event_type_display}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                                            <strong style="color: #495057;">📅 Tarih:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                                            {event_date}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                                            <strong style="color: #495057;">⏰ Saat:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                                            {event_time}
                                        </td>
                                    </tr>
                                    {extra_info_html}
                                </table>

                                {description_html}

                                <!-- CTA Button -->
                                <table role="presentation" style="margin: 30px auto 0;">
                                    <tr>
                                        <td style="text-align: center;">
                                            <a href="https://www.kaplanhukukotomasyon.com/takvim" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #ffffff; padding: 14px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px rgba(30, 60, 114, 0.3);">
                                                📅 Takvimi Görüntüle
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #1a1a1a; padding: 25px 30px; text-align: center;">
                                <p style="color: #ffffff; font-size: 14px; margin: 0 0 8px 0;">
                                    <strong>Kaplan Hukuk Otomasyonu</strong>
                                </p>
                                <p style="color: #999999; font-size: 12px; margin: 0 0 12px 0;">
                                    Bu e-posta otomatik olarak gönderilmiştir.
                                </p>
                                <p style="color: #666666; font-size: 11px; margin: 0;">
                                    <a href="https://www.kaplanhukukotomasyon.com" style="color: #2a5298; text-decoration: none;">www.kaplanhukukotomasyon.com</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>"""

    return send_email(user_email, subject, body, is_html=True)

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
        'diger': 'Diğer',
        'arabuluculuk-toplantisi': 'Arabuluculuk Toplantısı',
        'gunluk-kayit': 'Günlük Kayıt'
    }

    event_type_icons = {
        'durusma': '⚖️',
        'e-durusma': '💻',
        'tahliye': '🏠',
        'is': '📋',
        'randevu': '👥',
        'diger': '📌',
        'arabuluculuk-toplantisi': '🤝',
        'gunluk-kayit': '📝'
    }

    event_type_display = event_type_names.get(event_type, event_type)
    event_icon = event_type_icons.get(event_type, '📌')

    subject = f"⏰ Etkinlik Hatırlatması: {event_title}"

    # Ek bilgiler için HTML satırları
    extra_info_html = ""

    if event_type in ['durusma', 'e-durusma']:
        if courthouse:
            extra_info_html += f"""
            <tr>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                    <strong style="color: #495057;">🏛️ Adliye:</strong>
                </td>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                    {courthouse}
                </td>
            </tr>"""
        if department:
            extra_info_html += f"""
            <tr>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                    <strong style="color: #495057;">⚖️ Mahkeme/Birim:</strong>
                </td>
                <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                    {department}
                </td>
            </tr>"""

    description_html = ""
    if description and description.strip():
        description_html = f"""
        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 4px; margin-top: 30px;">
            <p style="color: #856404; font-size: 14px; margin: 0 0 10px 0;">
                <strong>📝 Açıklama:</strong>
            </p>
            <p style="color: #212529; font-size: 14px; margin: 0; line-height: 1.6;">
                {description.strip()}
            </p>
        </div>"""

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 12px; overflow: hidden;">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); padding: 40px 30px; text-align: center;">
                                <img src="https://www.kaplanhukukotomasyon.com/static/images/logo.png" alt="Kaplan Hukuk Otomasyonu" style="max-width: 180px; height: auto; margin-bottom: 20px;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">⏰ Etkinlik Hatırlatması</h1>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <p style="color: #333333; font-size: 16px; margin: 0 0 25px 0;">
                                    Merhaba <strong style="color: #ff6b35;">{user_name}</strong>,
                                </p>
                                <p style="color: #555555; font-size: 15px; margin: 0 0 30px 0;">
                                    Size atanan etkinlik yaklaşıyor:
                                </p>

                                <!-- Alert Box -->
                                <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%); border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                                    <p style="color: #856404; font-size: 15px; font-weight: 600; margin: 0;">
                                        ⚠️ Bu etkinlik yakında başlayacak, lütfen hazırlıklarınızı tamamlayınız!
                                    </p>
                                </div>

                                <!-- Event Details Table -->
                                <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; margin-bottom: 20px;">
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; background-color: #f8f9fa;">
                                            <strong style="color: #495057;">{event_icon} Etkinlik:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; background-color: #f8f9fa; color: #ff6b35; font-weight: 600;">
                                            {event_title}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                                            <strong style="color: #495057;">📋 Türü:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                                            {event_type_display}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                                            <strong style="color: #495057;">📅 Tarih:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529;">
                                            {event_date}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef;">
                                            <strong style="color: #495057;">⏰ Saat:</strong>
                                        </td>
                                        <td style="padding: 12px 20px; border-bottom: 1px solid #e9ecef; color: #212529; font-weight: 600;">
                                            {event_time}
                                        </td>
                                    </tr>
                                    {extra_info_html}
                                </table>

                                {description_html}

                                <!-- CTA Button -->
                                <table role="presentation" style="margin: 30px auto 0;">
                                    <tr>
                                        <td style="text-align: center;">
                                            <a href="https://www.kaplanhukukotomasyon.com/takvim" style="background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: #ffffff; padding: 14px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px rgba(255, 107, 53, 0.3);">
                                                📅 Takvimi Görüntüle
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #1a1a1a; padding: 25px 30px; text-align: center;">
                                <p style="color: #ffffff; font-size: 14px; margin: 0 0 8px 0;">
                                    <strong>Kaplan Hukuk Otomasyonu</strong>
                                </p>
                                <p style="color: #999999; font-size: 12px; margin: 0 0 12px 0;">
                                    Bu e-posta otomatik olarak gönderilmiştir.
                                </p>
                                <p style="color: #666666; font-size: 11px; margin: 0;">
                                    <a href="https://www.kaplanhukukotomasyon.com" style="color: #f7931e; text-decoration: none;">www.kaplanhukukotomasyon.com</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>"""

    return send_email(user_email, subject, body, is_html=True)

if __name__ == "__main__":
    # Test e-postasi gonder
    print("Test e-postasi gonderiliyor...")
    success, message = send_test_email()
    
    if success:
        print(f"Basarili: {message}")
    else:
        print(f"Hata: {message}")