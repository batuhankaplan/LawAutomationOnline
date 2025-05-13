import sqlite3

# Veritabanı bağlantısını kur
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

try:
    # Sütun var mı kontrol et
    cursor.execute("PRAGMA table_info(document)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'pdf_version' not in column_names:
        # ALTER TABLE komutu ile sütunu ekle
        cursor.execute('ALTER TABLE document ADD COLUMN pdf_version TEXT')
        conn.commit()
        print("pdf_version sütunu başarıyla eklendi!")
    else:
        print("pdf_version sütunu zaten mevcut.")
except Exception as e:
    print(f"Bir hata oluştu: {str(e)}")
finally:
    # Bağlantıyı kapat
    conn.close() 