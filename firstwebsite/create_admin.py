from app import app, db
from models import User
from datetime import datetime

def create_admin_user():
    with app.app_context():
        # Mevcut admin kullanıcısını kontrol et
        admin = User.query.filter_by(email='admin@kaplanhukuk.com').first()
        
        if admin:
            print("Admin kullanıcısı zaten mevcut.")
            # Admin kullanıcısının yetkilerini güncelle
            admin.is_admin = True
            admin.is_approved = True
            admin.permissions = {
                'takvim_goruntule': True,
                'etkinlik_ekle': True,
                'etkinlik_duzenle': True,
                'etkinlik_sil': True,
                'etkinlik_goruntule': True,
                'duyuru_goruntule': True,
                'duyuru_ekle': True,
                'duyuru_duzenle': True,
                'duyuru_sil': True,
                'odeme_goruntule': True,
                'odeme_ekle': True,
                'odeme_duzenle': True,
                'odeme_sil': True,
                'dosya_sorgula': True,
                'dosya_ekle': True,
                'dosya_duzenle': True,
                'dosya_sil': True,
                'faiz_hesaplama': True,
                'harc_hesaplama': True,
                'isci_hesaplama': True,
                'vekalet_hesaplama': True,
                'ceza_infaz_hesaplama': True
            }
            db.session.commit()
            print("Admin kullanıcısının yetkileri güncellendi.")
        else:
            # Yeni admin kullanıcısı oluştur
            admin = User(
                email='admin@kaplanhukuk.com',
                username='admin',
                first_name='Admin',
                last_name='Kullanıcısı',
                role='Yönetici Avukat',
                gender='erkek',
                phone='5555555555',
                birthdate=datetime(1990, 1, 1).date(),
                is_admin=True,
                is_approved=True,
                approval_date=datetime.now(),
                permissions={
                    'takvim_goruntule': True,
                    'etkinlik_ekle': True,
                    'etkinlik_duzenle': True,
                    'etkinlik_sil': True,
                    'etkinlik_goruntule': True,
                    'duyuru_goruntule': True,
                    'duyuru_ekle': True,
                    'duyuru_duzenle': True,
                    'duyuru_sil': True,
                    'odeme_goruntule': True,
                    'odeme_ekle': True,
                    'odeme_duzenle': True,
                    'odeme_sil': True,
                    'dosya_sorgula': True,
                    'dosya_ekle': True,
                    'dosya_duzenle': True,
                    'dosya_sil': True,
                    'faiz_hesaplama': True,
                    'harc_hesaplama': True,
                    'isci_hesaplama': True,
                    'vekalet_hesaplama': True,
                    'ceza_infaz_hesaplama': True
                }
            )
            admin.set_password('Pemus3458')
            db.session.add(admin)
            db.session.commit()
            print("Yeni admin kullanıcısı oluşturuldu.")

if __name__ == '__main__':
    create_admin_user() 