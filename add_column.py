import sqlite3

# Local SQLite veritabanına toplanti_adresi kolonu ekle
conn = sqlite3.connect('firstwebsite/instance/database.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE calendar_event ADD COLUMN toplanti_adresi VARCHAR(500)')
    conn.commit()
    print("OK: toplanti_adresi kolonu basariyla eklendi!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("UYARI: Kolon zaten mevcut.")
    else:
        print(f"HATA: {e}")
finally:
    conn.close()