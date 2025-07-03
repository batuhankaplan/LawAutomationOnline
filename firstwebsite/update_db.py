from app import app, db
from models import CaseFile, Document, Expense, ActivityLog, CalendarEvent, User

def clean_database():
    """Veritabanındaki tüm dosya kayıtlarını temizle"""
    with app.app_context():
        try:
            print("Veritabanı temizleniyor...")
            
            # Dosya ile ilgili tabloları temizle
            ActivityLog.query.filter_by(activity_type='dosya_ekleme').delete()
            print("- Dosya ekleme logları silindi")
            
            Document.query.delete()
            print("- Belgeler silindi")
            
            Expense.query.delete()
            print("- Masraflar silindi")
            
            # Calendar eventleri temizle (duruşma bilgilerini içerenler)
            CalendarEvent.query.filter(CalendarEvent.file_type.isnot(None)).delete()
            print("- Duruşma etkinlikleri silindi")
            
            CaseFile.query.delete()
            print("- Dosyalar silindi")
            
            db.session.commit()
            print("✅ Veritabanı başarıyla temizlendi!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")

def clean_all_users():
    """Tüm kullanıcıları temizle"""
    with app.app_context():
        try:
            print("Kullanıcılar temizleniyor...")
            
            # Tüm kullanıcıları sil
            User.query.delete()
            print("- Tüm kullanıcılar silindi")
            
            db.session.commit()
            print("✅ Kullanıcılar başarıyla temizlendi!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")

def recreate_tables():
    """Tabloları yeniden oluştur"""
    with app.app_context():
        try:
            print("Tablolar yeniden oluşturuluyor...")
            db.create_all()
            print("✅ Tablolar başarıyla oluşturuldu!")
        except Exception as e:
            print(f"❌ Hata: {str(e)}")

if __name__ == "__main__":
    print("=== VERİTABANI YÖNETİMİ ===")
    print("1. Veritabanını temizle")
    print("2. Tabloları yeniden oluştur")
    print("3. Her ikisini de yap")
    print("4. Kullanıcıları temizle")
    print("5. Hem veritabanını hem kullanıcıları temizle")
    
    choice = input("Seçiminizi yapın (1/2/3/4/5): ")
    
    if choice == "1":
        clean_database()
    elif choice == "2":
        recreate_tables()
    elif choice == "3":
        clean_database()
        recreate_tables()
    elif choice == "4":
        clean_all_users()
    elif choice == "5":
        clean_database()
        clean_all_users()
        recreate_tables()
    else:
        print("Geçersiz seçim!")
