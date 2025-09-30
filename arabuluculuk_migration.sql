-- Arabuluculuk Toplantısı alanlarını CalendarEvent tablosuna ekle
ALTER TABLE calendar_event ADD COLUMN basvuran_isim VARCHAR(200);
ALTER TABLE calendar_event ADD COLUMN basvuran_telefon VARCHAR(20);
ALTER TABLE calendar_event ADD COLUMN aleyhindeki_isim VARCHAR(200);
ALTER TABLE calendar_event ADD COLUMN aleyhindeki_telefon VARCHAR(20);
ALTER TABLE calendar_event ADD COLUMN arabulucu_isim VARCHAR(200);
ALTER TABLE calendar_event ADD COLUMN arabulucu_telefon VARCHAR(20);
ALTER TABLE calendar_event ADD COLUMN arabuluculuk_turu VARCHAR(50);
