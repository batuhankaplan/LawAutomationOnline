import sqlite3
import os

def migrate_ornek_sozlesme_pdf_path():
    """Örnek sözleşme tablosuna pdf_path alanı ekle"""
    db_path = os.path.join('firstwebsite', 'instance', 'database.db')
    
    if not os.path.exists(db_path):
        print(f"Database dosyasi bulunamadi: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Mevcut kolonları kontrol et
        cursor.execute("PRAGMA table_info(ornek_sozlesme)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # pdf_path kolonunu ekle
        if 'pdf_path' not in columns:
            sql = "ALTER TABLE ornek_sozlesme ADD COLUMN pdf_path VARCHAR(500)"
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
    migrate_ornek_sozlesme_pdf_path()

