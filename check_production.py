#!/usr/bin/env python3
"""
Production Sunucu Diagnostic Script
DigitalOcean üzerinde çalıştırın: python check_production.py
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("🔍 PRODUCTION SUNUCU DİAGNOSTİK RAPORU")
print("=" * 60)
print()

# 1. Environment Variables
print("📋 1. ENVIRONMENT VARIABLES")
print("-" * 60)

env_vars = [
    'DATABASE_URL',
    'UPLOAD_FOLDER',
    'SECRET_KEY',
    'DEBUG',
    'MAIL_SERVER',
    'GEMINI_API_KEY'
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Şifre/secret içeren değerleri maskele
        if any(x in var.upper() for x in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']):
            display = value[:10] + '...' + value[-5:] if len(value) > 15 else '***'
        elif 'DATABASE_URL' in var:
            # postgresql://user:pass@host:port/db → postgresql://user:***@host:port/db
            if '@' in value:
                parts = value.split('@')
                before = parts[0].split(':')[0] + '://***:***'
                display = before + '@' + '@'.join(parts[1:])
            else:
                display = '***'
        else:
            display = value
        print(f"✅ {var}: {display}")
    else:
        print(f"❌ {var}: NOT SET")

print()

# 2. Database Check
print("📊 2. DATABASE BAĞLANTISI")
print("-" * 60)

try:
    # Flask app import et
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'firstwebsite'))
    from app import app, db

    with app.app_context():
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI')

        if 'sqlite' in db_url.lower():
            print("❌ SQLite kullanılıyor (YANLIŞ!)")
            print(f"   URL: {db_url}")
        elif 'postgresql' in db_url.lower():
            print("✅ PostgreSQL kullanılıyor (DOĞRU!)")
            # Host ve database adını göster
            if '@' in db_url:
                host_part = db_url.split('@')[1].split('/')[0]
                db_part = db_url.split('/')[-1].split('?')[0]
                print(f"   Host: {host_part}")
                print(f"   Database: {db_part}")
        else:
            print(f"⚠️  Bilinmeyen database: {db_url[:50]}...")

        # Bağlantı testi
        try:
            db.engine.connect()
            print("✅ Database bağlantısı BAŞARILI")
        except Exception as e:
            print(f"❌ Database bağlantısı BAŞARISIZ: {str(e)[:100]}")

except Exception as e:
    print(f"❌ Flask app import hatası: {str(e)[:100]}")

print()

# 3. Upload Folders
print("📁 3. UPLOAD KLASÖRLERI")
print("-" * 60)

upload_folder = os.getenv('UPLOAD_FOLDER', 'uploads')
if not os.path.isabs(upload_folder):
    upload_folder = os.path.join(os.getcwd(), upload_folder)

upload_paths = [
    ('Main uploads', upload_folder),
    ('Documents', os.path.join(upload_folder, 'documents')),
    ('Ornek Dilekce', os.path.join(upload_folder, 'ornek_dilekceler')),
    ('Profile pics', os.path.join(upload_folder, 'profile_pics')),
]

for name, path in upload_paths:
    exists = os.path.exists(path)
    writable = os.access(path, os.W_OK) if exists else False

    if exists and writable:
        file_count = len(list(Path(path).rglob('*'))) if os.path.isdir(path) else 0
        print(f"✅ {name}: {path}")
        print(f"   Dosya sayısı: {file_count}")
    elif exists:
        print(f"⚠️  {name}: {path} (YAZMA İZNİ YOK)")
    else:
        print(f"❌ {name}: {path} (BULUNAMADI)")

print()

# 4. File Permissions
print("🔐 4. İZİNLER")
print("-" * 60)

if os.path.exists(upload_folder):
    stat_info = os.stat(upload_folder)
    import pwd
    try:
        owner = pwd.getpwuid(stat_info.st_uid).pw_name
    except:
        owner = stat_info.st_uid

    perms = oct(stat_info.st_mode)[-3:]
    print(f"Owner: {owner}")
    print(f"Permissions: {perms}")
    print(f"Writable: {'✅ Yes' if os.access(upload_folder, os.W_OK) else '❌ No'}")
else:
    print("❌ Upload folder bulunamadı")

print()

# 5. .env Dosyası
print("⚙️  5. .ENV DOSYASI")
print("-" * 60)

env_path = os.path.join(os.path.dirname(__file__), 'firstwebsite', '.env')
if os.path.exists(env_path):
    print(f"✅ .env dosyası bulundu: {env_path}")
    with open(env_path, 'r') as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
    print(f"   Ayar sayısı: {len(lines)}")
    print("   Ayarlar:")
    for line in lines:
        if '=' in line:
            key = line.split('=')[0]
            print(f"   - {key}")
else:
    print(f"❌ .env dosyası BULUNAMADI: {env_path}")

print()

# 6. Recent Uploads Test
print("📤 6. SON YÜKLENEN DOSYALAR")
print("-" * 60)

if os.path.exists(upload_folder):
    from datetime import datetime
    recent_files = []

    for root, dirs, files in os.walk(upload_folder):
        for file in files[:20]:  # İlk 20 dosya
            filepath = os.path.join(root, file)
            mtime = os.path.getmtime(filepath)
            recent_files.append((filepath, mtime))

    recent_files.sort(key=lambda x: x[1], reverse=True)

    if recent_files:
        print("Son 5 dosya:")
        for filepath, mtime in recent_files[:5]:
            dt = datetime.fromtimestamp(mtime)
            rel_path = os.path.relpath(filepath, upload_folder)
            print(f"  {dt:%Y-%m-%d %H:%M} - {rel_path}")
    else:
        print("⚠️  Hiç dosya yok")
else:
    print("❌ Upload folder yok")

print()

# 7. Özet
print("=" * 60)
print("📝 ÖZET VE ÖNERİLER")
print("=" * 60)

issues = []
fixes = []

if not os.getenv('DATABASE_URL'):
    issues.append("DATABASE_URL environment variable eksik")
    fixes.append("DigitalOcean PostgreSQL bağlantı bilgilerini .env'ye ekleyin")

if not os.path.exists(upload_folder):
    issues.append("Upload folder bulunamadı")
    fixes.append(f"mkdir -p {upload_folder} && chown www-data:www-data {upload_folder}")

if os.path.exists(upload_folder) and not os.access(upload_folder, os.W_OK):
    issues.append("Upload folder'a yazma izni yok")
    fixes.append(f"chown -R www-data:www-data {upload_folder}")

if issues:
    print("❌ SORUNLAR:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    print()
    print("🔧 ÇÖZÜMLER:")
    for i, fix in enumerate(fixes, 1):
        print(f"   {i}. {fix}")
else:
    print("✅ Herşey yolunda görünüyor!")

print()
print("=" * 60)
print("Rapor tamamlandı.")
print("=" * 60)
