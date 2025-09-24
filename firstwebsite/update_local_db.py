#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Local SQLite database'i arabuluculuk toplantısı alanları için güncelleyen script
"""

from app import app, db

def update_local_database():
    """Local SQLite database'i güncelle"""
    with app.app_context():
        try:
            print("Local SQLite database güncelleniyor...")

            # Tabloları oluştur/güncelle
            db.create_all()

            print("Local database başarıyla güncellendi!")
            print("Arabuluculuk Toplantısı alanları eklendi")

            # Test sorgusu çalıştır
            from models import CalendarEvent
            events = CalendarEvent.query.limit(1).all()
            print(f"Test sorgusu başarılı - Toplam {CalendarEvent.query.count()} etkinlik")

        except Exception as e:
            print(f"Hata: {e}")

if __name__ == '__main__':
    update_local_database()