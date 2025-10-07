import sqlite3
import os

def migrate_isci_gorusme_pdf_path():
    """İşçi görüşme tutanağı tablosuna pdf_path alanı ekle"""
    db_path = os.path.join('firstwebsite', 'instance', 'database.db')
    
    if not os.path.exists(db_path):
        print(f"Database dosyası bulunamadı: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Mevcut kolonları kontrol et
        cursor.execute("PRAGMA table_info(isci_gorusme_tutanagi)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # pdf_path kolonunu ekle
        if 'pdf_path' not in columns:
            sql = "ALTER TABLE isci_gorusme_tutanagi ADD COLUMN pdf_path VARCHAR(500)"
            print(f"Ekleniyor: pdf_path")
            cursor.execute(sql)
            print("OK - pdf_path kolonu basariyla eklendi")
        else:
            print("OK - pdf_path kolonu zaten mevcut")
        
        conn.commit()
        print("\nOK - Migration basariyla tamamlandi!")
        
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_isci_gorusme_pdf_path()

