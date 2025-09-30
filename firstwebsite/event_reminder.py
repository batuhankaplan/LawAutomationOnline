#!/usr/bin/env python3
"""
Calendar Event Reminder System
Bu script takvim etkinlikleri için hatırlatma e-postaları gönderir.
Cron job olarak çalıştırılabilir.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
from models import db, CalendarEvent, User
from email_utils import send_calendar_event_reminder_email
from app import app
import logging

# Logger ayarla
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reminder_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def send_event_reminders():
    """
    Yarın gerçekleşecek etkinlikler için hatırlatma e-postaları gönder
    """
    with app.app_context():
        try:
            # Yarının tarihi
            tomorrow = datetime.now().date() + timedelta(days=1)
            
            # Yarın gerçekleşecek etkinlikleri getir
            events = CalendarEvent.query.filter(
                CalendarEvent.date == tomorrow,
                CalendarEvent.is_completed == False,
                CalendarEvent.assigned_to.isnot(None)
            ).all()
            
            logger.info(f"Yarın için {len(events)} etkinlik bulundu.")
            
            sent_count = 0
            error_count = 0
            
            for event in events:
                try:
                    # Atanan kişiyi bul
                    assigned_user = None
                    
                    # Önce tam isim eşleşmesi dene
                    for user in User.query.filter_by(is_approved=True).all():
                        if user.get_full_name() == event.assigned_to:
                            assigned_user = user
                            break
                    
                    if not assigned_user:
                        # Alternatif olarak isim parçaları ile dene
                        name_parts = event.assigned_to.replace('Av. ', '').replace('Stj. Av. ', '').replace('Asst. ', '').replace('Ulşm. ', '').replace('Tkp El. ', '').split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = ' '.join(name_parts[1:])
                            assigned_user = User.query.filter_by(
                                is_approved=True,
                                first_name=first_name,
                                last_name=last_name
                            ).first()
                    
                    if assigned_user:
                        # Atayan bilgisini al
                        assigned_by = None
                        if event.user_id:
                            assigner = User.query.get(event.user_id)
                            if assigner:
                                assigned_by = assigner.get_full_name()

                        success = send_calendar_event_reminder_email(
                            user_email=assigned_user.email,
                            user_name=assigned_user.get_full_name(),
                            event_title=event.title,
                            event_date=event.date.strftime('%d.%m.%Y'),
                            event_time=event.time.strftime('%H:%M'),
                            event_type=event.event_type,
                            courthouse=event.courthouse,
                            department=event.department,
                            description=event.description,
                            arabuluculuk_turu=event.arabuluculuk_turu,
                            toplanti_adresi=event.toplanti_adresi,
                            assigned_by_name=assigned_by
                        )
                        
                        if success:
                            sent_count += 1
                            logger.info(f"Hatırlatma e-postası gönderildi: {assigned_user.email} - {event.title}")
                        else:
                            error_count += 1
                            logger.error(f"E-posta gönderme başarısız: {assigned_user.email} - {event.title}")
                    else:
                        logger.warning(f"Atanan kullanıcı bulunamadı: {event.assigned_to} - {event.title}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Etkinlik işleme hatası: {event.title} - {str(e)}")
                    error_count += 1
            
            logger.info(f"Hatırlatma işlemi tamamlandı. Gönderilen: {sent_count}, Hata: {error_count}")
            return sent_count, error_count
            
        except Exception as e:
            logger.error(f"Hatırlatma sistemi hatası: {str(e)}")
            return 0, 1

def send_today_reminders():
    """
    Bugün gerçekleşecek etkinlikler için hatırlatma e-postaları gönder
    """
    with app.app_context():
        try:
            # Bugünün tarihi
            today = datetime.now().date()
            
            # Bugün gerçekleşecek etkinlikleri getir
            events = CalendarEvent.query.filter(
                CalendarEvent.date == today,
                CalendarEvent.is_completed == False,
                CalendarEvent.assigned_to.isnot(None)
            ).all()
            
            logger.info(f"Bugün için {len(events)} etkinlik bulundu.")
            
            sent_count = 0
            error_count = 0
            
            for event in events:
                try:
                    # Atanan kişiyi bul
                    assigned_user = None
                    
                    # Önce tam isim eşleşmesi dene
                    for user in User.query.filter_by(is_approved=True).all():
                        if user.get_full_name() == event.assigned_to:
                            assigned_user = user
                            break
                    
                    if not assigned_user:
                        # Alternatif olarak isim parçaları ile dene
                        name_parts = event.assigned_to.replace('Av. ', '').replace('Stj. Av. ', '').replace('Asst. ', '').replace('Ulşm. ', '').replace('Tkp El. ', '').split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = ' '.join(name_parts[1:])
                            assigned_user = User.query.filter_by(
                                is_approved=True,
                                first_name=first_name,
                                last_name=last_name
                            ).first()
                    
                    if assigned_user:
                        # Atayan bilgisini al
                        assigned_by = None
                        if event.user_id:
                            assigner = User.query.get(event.user_id)
                            if assigner:
                                assigned_by = assigner.get_full_name()

                        success = send_calendar_event_reminder_email(
                            user_email=assigned_user.email,
                            user_name=assigned_user.get_full_name(),
                            event_title=event.title,
                            event_date=event.date.strftime('%d.%m.%Y'),
                            event_time=event.time.strftime('%H:%M'),
                            event_type=event.event_type,
                            courthouse=event.courthouse,
                            department=event.department,
                            description=event.description,
                            arabuluculuk_turu=event.arabuluculuk_turu,
                            toplanti_adresi=event.toplanti_adresi,
                            assigned_by_name=assigned_by
                        )
                        
                        if success:
                            sent_count += 1
                            logger.info(f"Bugün hatırlatma e-postası gönderildi: {assigned_user.email} - {event.title}")
                        else:
                            error_count += 1
                            logger.error(f"E-posta gönderme başarısız: {assigned_user.email} - {event.title}")
                    else:
                        logger.warning(f"Atanan kullanıcı bulunamadı: {event.assigned_to} - {event.title}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Etkinlik işleme hatası: {event.title} - {str(e)}")
                    error_count += 1
            
            logger.info(f"Bugün hatırlatma işlemi tamamlandı. Gönderilen: {sent_count}, Hata: {error_count}")
            return sent_count, error_count
            
        except Exception as e:
            logger.error(f"Hatırlatma sistemi hatası: {str(e)}")
            return 0, 1

if __name__ == "__main__":
    print("Calendar Event Reminder System")
    print("1. Yarın için hatırlatma gönder")
    print("2. Bugün için hatırlatma gönder")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "tomorrow":
            sent, errors = send_event_reminders()
            print(f"Yarın hatırlatmaları - Gönderilen: {sent}, Hata: {errors}")
        elif sys.argv[1] == "today":
            sent, errors = send_today_reminders()
            print(f"Bugün hatırlatmaları - Gönderilen: {sent}, Hata: {errors}")
        else:
            print("Geçersiz parametre. 'tomorrow' veya 'today' kullanın.")
    else:
        choice = input("Seçiminizi yapın (1 veya 2): ")
        if choice == "1":
            sent, errors = send_event_reminders()
            print(f"Yarın hatırlatmaları - Gönderilen: {sent}, Hata: {errors}")
        elif choice == "2":
            sent, errors = send_today_reminders()
            print(f"Bugün hatırlatmaları - Gönderilen: {sent}, Hata: {errors}")
        else:
            print("Geçersiz seçim.")