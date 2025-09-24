-- CaseFile tablosuna city alanı ekleme migration'ı
ALTER TABLE case_file ADD COLUMN city VARCHAR(50);

-- Mevcut courthouse verilerinden şehir bilgisini çıkarmaya çalış
UPDATE case_file
SET city = 'İstanbul'
WHERE courthouse LIKE '%İstanbul%' OR courthouse LIKE '%Şile%' OR courthouse LIKE '%Beylikdüzü%'
   OR courthouse LIKE '%Silivri%' OR courthouse LIKE '%Çatalca%' OR courthouse LIKE '%Kartal%'
   OR courthouse LIKE '%Pendik%' OR courthouse LIKE '%Tuzla%' OR courthouse LIKE '%Maltepe%'
   OR courthouse LIKE '%Ataşehir%' OR courthouse LIKE '%Ümraniye%' OR courthouse LIKE '%Üsküdar%'
   OR courthouse LIKE '%Kadıköy%';

UPDATE case_file
SET city = 'Ankara'
WHERE courthouse LIKE '%Ankara%';

UPDATE case_file
SET city = 'İzmir'
WHERE courthouse LIKE '%İzmir%';

-- Diğer şehirler için courthouse alanından şehir ismi çıkarmaya çalış
-- Courthouse formatı "ŞEHİR - ADLİYE" ise
UPDATE case_file
SET city = TRIM(SUBSTRING_INDEX(courthouse, ' - ', 1))
WHERE city IS NULL AND courthouse LIKE '% - %';

-- Eğer hala boşsa 'Bilinmiyor' yap
UPDATE case_file
SET city = 'Bilinmiyor'
WHERE city IS NULL OR city = '';