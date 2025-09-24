#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQLite database migration script to add mediation meeting columns
"""

import sqlite3
import os

def migrate_sqlite_database():
    """SQLite database'i mediation alanları için güncelle"""

    # Database dosyasının yolunu bul
    db_path = os.path.join('instance', 'database.db')

    if not os.path.exists(db_path):
        print(f"Database dosyası bulunamadı: {db_path}")
        return

    try:
        print("SQLite database migration başlatılıyor...")

        # SQLite bağlantısı
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Mevcut sütunları kontrol et
        cursor.execute("PRAGMA table_info(calendar_event)")
        columns = [column[1] for column in cursor.fetchall()]

        # Eklenecek sütunlar
        new_columns = [
            ("basvuran_ad_soyad", "VARCHAR(200)"),
            ("basvuran_telefon", "VARCHAR(20)"),
            ("karsi_taraf_ad_soyad", "VARCHAR(200)"),
            ("karsi_taraf_telefon", "VARCHAR(20)"),
            ("arabulucu_ad_soyad", "VARCHAR(200)"),
            ("arabulucu_telefon", "VARCHAR(20)"),
            ("yuzyuze", "BOOLEAN DEFAULT 0"),
            ("telekonferans", "BOOLEAN DEFAULT 0")
        ]

        # Her sütunu kontrol et ve ekle
        for column_name, column_type in new_columns:
            if column_name not in columns:
                sql = f"ALTER TABLE calendar_event ADD COLUMN {column_name} {column_type}"
                print(f"Ekleniyor: {column_name}")
                cursor.execute(sql)
            else:
                print(f"Zaten mevcut: {column_name}")

        # Değişiklikleri kaydet
        conn.commit()

        # Test sorgusu
        cursor.execute("SELECT COUNT(*) FROM calendar_event")
        count = cursor.fetchone()[0]

        print(f"Migration tamamlandı! Toplam {count} etkinlik mevcut.")
        print("Arabuluculuk Toplantısı alanları başarıyla eklendi!")

    except Exception as e:
        print(f"Hata: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_sqlite_database()