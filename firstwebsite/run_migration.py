#!/usr/bin/env python3
"""
Database migration script to add city field to CaseFile table
"""
import sqlite3
import os

def run_migration():
    # Database dosyasının yolu
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

    if not os.path.exists(db_path):
        print(f"Database dosyası bulunamadı: {db_path}")
        return False

    try:
        # Database'e bağlan
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Migration başlatılıyor...")

        # City alanını ekle
        print("1. City alanı ekleniyor...")
        cursor.execute("ALTER TABLE case_file ADD COLUMN city VARCHAR(50)")

        # İstanbul için güncelle
        print("2. İstanbul kayıtları güncelleniyor...")
        istanbul_conditions = [
            "courthouse LIKE '%İstanbul%'", "courthouse LIKE '%Şile%'",
            "courthouse LIKE '%Beylikdüzü%'", "courthouse LIKE '%Silivri%'",
            "courthouse LIKE '%Çatalca%'", "courthouse LIKE '%Kartal%'",
            "courthouse LIKE '%Pendik%'", "courthouse LIKE '%Tuzla%'",
            "courthouse LIKE '%Maltepe%'", "courthouse LIKE '%Ataşehir%'",
            "courthouse LIKE '%Ümraniye%'", "courthouse LIKE '%Üsküdar%'",
            "courthouse LIKE '%Kadıköy%'"
        ]

        cursor.execute(f"""
            UPDATE case_file
            SET city = 'İstanbul'
            WHERE {' OR '.join(istanbul_conditions)}
        """)

        # Ankara için güncelle
        print("3. Ankara kayıtları güncelleniyor...")
        cursor.execute("UPDATE case_file SET city = 'Ankara' WHERE courthouse LIKE '%Ankara%'")

        # İzmir için güncelle
        print("4. İzmir kayıtları güncelleniyor...")
        cursor.execute("UPDATE case_file SET city = 'İzmir' WHERE courthouse LIKE '%İzmir%'")

        # "ŞEHİR - ADLİYE" formatındakileri çıkar
        print("5. Diğer şehirler için courthouse'dan şehir çıkarılıyor...")
        cursor.execute("""
            UPDATE case_file
            SET city = TRIM(SUBSTR(courthouse, 1, INSTR(courthouse, ' - ') - 1))
            WHERE city IS NULL AND courthouse LIKE '% - %'
        """)

        # Boşları 'Bilinmiyor' yap
        print("6. Boş kayıtlar 'Bilinmiyor' olarak ayarlanıyor...")
        cursor.execute("UPDATE case_file SET city = 'Bilinmiyor' WHERE city IS NULL OR city = ''")

        # Değişiklikleri kaydet
        conn.commit()

        # Sonuçları kontrol et
        cursor.execute("SELECT COUNT(*) FROM case_file WHERE city IS NOT NULL")
        updated_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM case_file")
        total_count = cursor.fetchone()[0]

        print(f"\nMigration tamamlandı!")
        print(f"Toplam kayıt: {total_count}")
        print(f"City alanı dolu olan kayıt: {updated_count}")

        # Örnek kayıtları göster
        print("\nÖrnek kayıtlar:")
        cursor.execute("SELECT city, courthouse FROM case_file LIMIT 5")
        samples = cursor.fetchall()
        for city, courthouse in samples:
            print(f"  Şehir: {city} | Adliye: {courthouse}")

        conn.close()
        return True

    except sqlite3.Error as e:
        if "duplicate column name" in str(e).lower():
            print("City alanı zaten mevcut, sadece veri güncellemesi yapılıyor...")
            try:
                # Sadece veri güncelleme kısmını çalıştır
                cursor.execute("UPDATE case_file SET city = 'İstanbul' WHERE city IS NULL AND (" + ' OR '.join(istanbul_conditions) + ")")
                cursor.execute("UPDATE case_file SET city = 'Ankara' WHERE city IS NULL AND courthouse LIKE '%Ankara%'")
                cursor.execute("UPDATE case_file SET city = 'İzmir' WHERE city IS NULL AND courthouse LIKE '%İzmir%'")
                cursor.execute("UPDATE case_file SET city = 'Bilinmiyor' WHERE city IS NULL OR city = ''")
                conn.commit()
                conn.close()
                print("Veri güncellemesi tamamlandı!")
                return True
            except Exception as update_error:
                print(f"Veri güncellemesi hatası: {update_error}")
                return False
        else:
            print(f"Migration hatası: {e}")
            return False
    except Exception as e:
        print(f"Beklenmeyen hata: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n✅ Migration başarılı! Uygulamayı yeniden başlatabilirsiniz.")
    else:
        print("\n❌ Migration başarısız!")