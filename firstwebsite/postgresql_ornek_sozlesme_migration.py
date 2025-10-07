"""
PostgreSQL için örnek sözleşme PDF path migration scripti
DigitalOcean'da çalıştırmak için
"""
import psycopg2
import os
from dotenv import load_dotenv

def migrate_postgresql_ornek_sozlesme_pdf_path():
    """PostgreSQL database'ine pdf_path kolonunu ekle"""
    
    # .env dosyasını yükle
    load_dotenv()
    
    # Database bağlantı bilgileri
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("HATA: DATABASE_URL environment variable bulunamadi!")
        print("PostgreSQL baglanti bilgilerini kontrol edin.")
        return
    
    try:
        # PostgreSQL'e baglan
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Mevcut kolonlari kontrol et
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ornek_sozlesme'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        # pdf_path kolonunu ekle
        if 'pdf_path' not in columns:
            sql = "ALTER TABLE ornek_sozlesme ADD COLUMN pdf_path VARCHAR(500)"
            print(f"Ekleniyor: pdf_path kolonu...")
            cursor.execute(sql)
            conn.commit()
            print("OK - pdf_path kolonu basariyla eklendi")
        else:
            print("OK - pdf_path kolonu zaten mevcut")
        
        print("\nOK - PostgreSQL migration basariyla tamamlandi!")
        
    except Exception as e:
        print(f"HATA: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_postgresql_ornek_sozlesme_pdf_path()

