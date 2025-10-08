-- PostgreSQL 17 Migration Script
-- Client tablosuna entity_type ve payment_date alanlarını ekler

-- Entity type alanını ekle (eğer yoksa)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'client' AND column_name = 'entity_type'
    ) THEN
        ALTER TABLE client ADD COLUMN entity_type VARCHAR(20) DEFAULT 'person';
        RAISE NOTICE 'entity_type sütunu eklendi';
    ELSE
        RAISE NOTICE 'entity_type sütunu zaten mevcut';
    END IF;
END $$;

-- Payment date alanını ekle (eğer yoksa)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'client' AND column_name = 'payment_date'
    ) THEN
        ALTER TABLE client ADD COLUMN payment_date DATE;
        RAISE NOTICE 'payment_date sütunu eklendi';
    ELSE
        RAISE NOTICE 'payment_date sütunu zaten mevcut';
    END IF;
END $$;

-- Mevcut kayıtlar için entity_type'ı güncelle (surname boş olanları company yap)
UPDATE client 
SET entity_type = 'company' 
WHERE (surname IS NULL OR surname = '' OR surname = '-') 
AND entity_type = 'person';

-- Başarı mesajı
DO $$
BEGIN
    RAISE NOTICE 'Migration başarıyla tamamlandı!';
END $$;

