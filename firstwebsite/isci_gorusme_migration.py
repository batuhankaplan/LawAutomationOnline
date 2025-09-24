#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQLite database migration script to add missing columns to isci_gorusme_tutanagi table
"""

import sqlite3
import os

def migrate_isci_gorusme_table():
    """İşçi Görüşme Tutanağı tablosuna eksik sütunları ekle"""

    # Database dosyasının yolunu bul
    db_path = os.path.join('instance', 'database.db')

    if not os.path.exists(db_path):
        print(f"Database dosyası bulunamadı: {db_path}")
        return

    try:
        print("İşçi Görüşme Tutanağı migration başlatılıyor...")

        # SQLite bağlantısı
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Mevcut sütunları kontrol et
        cursor.execute("PRAGMA table_info(isci_gorusme_tutanagi)")
        columns = [column[1] for column in cursor.fetchall()]

        # Eklenecek sütunlar
        new_columns = [
            ("companyAddress", "TEXT"),
            ("workingHours", "VARCHAR(100)"),
            ("overtime", "VARCHAR(100)"),
            ("weeklyHoliday", "VARCHAR(50)"),
            ("annualLeave", "VARCHAR(100)"),
            ("terminationReason", "TEXT"),
            ("terminationType", "VARCHAR(50)"),
            ("noticeCompliance", "VARCHAR(50)"),
            ("severancePay", "VARCHAR(50)"),
            ("noticePay", "VARCHAR(50)"),
            ("unpaidWages", "VARCHAR(50)"),
            ("overtimePay", "VARCHAR(50)"),
            ("annualLeavePay", "VARCHAR(50)"),
            ("ubgtPay", "VARCHAR(50)"),
            ("severancePayOption", "VARCHAR(10) DEFAULT 'no'"),
            ("noticePayOption", "VARCHAR(10) DEFAULT 'no'"),
            ("unpaidWagesOption", "VARCHAR(10) DEFAULT 'no'"),
            ("overtimePayOption", "VARCHAR(10) DEFAULT 'no'"),
            ("annualLeavePayOption", "VARCHAR(10) DEFAULT 'no'"),
            ("ubgtPayOption", "VARCHAR(10) DEFAULT 'no'"),
            ("workerStatement", "TEXT"),
            ("employerStatement", "TEXT"),
            ("witnessOption", "VARCHAR(10) DEFAULT 'no'"),
            ("witnesses", "TEXT"),
            ("created_at", "DATETIME"),
            ("updated_at", "DATETIME"),
            ("user_id", "INTEGER")
        ]

        # Her sütunu kontrol et ve ekle
        for column_name, column_type in new_columns:
            if column_name not in columns:
                sql = f"ALTER TABLE isci_gorusme_tutanagi ADD COLUMN {column_name} {column_type}"
                print(f"Ekleniyor: {column_name}")
                cursor.execute(sql)
            else:
                print(f"Zaten mevcut: {column_name}")

        # Değişiklikleri kaydet
        conn.commit()

        # Test sorgusu
        cursor.execute("SELECT COUNT(*) FROM isci_gorusme_tutanagi")
        count = cursor.fetchone()[0]

        print(f"Migration tamamlandı! Toplam {count} işçi görüşme tutanağı mevcut.")
        print("İşçi Görüşme Tutanağı tablosu başarıyla güncellendi!")

    except Exception as e:
        print(f"Hata: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_isci_gorusme_table()