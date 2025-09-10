#!/usr/bin/env python3
"""
Script to clean duplicate code blocks from app.py
"""

def clean_app_file():
    with open('firstwebsite/app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # İlk gerçek Flask app tanımını bul (4. tanım)
    app_definitions = []
    for i, line in enumerate(lines):
        if line.strip().startswith('app = Flask'):
            app_definitions.append(i)
    
    print(f"Found {len(app_definitions)} Flask app definitions at lines: {app_definitions}")
    
    if len(app_definitions) != 4:
        print("WARNING: Expected 4 app definitions, found", len(app_definitions))
        return
    
    # İlk 3 duplicate bloğu kaldır, sadece son bloğu tut
    # İlk bölüm: satır 0'dan 3. app tanımına kadar olan import'lar ve yardımcı fonksiyonlar
    # Son bölüm: 4. app tanımından dosya sonuna kadar
    
    # Import'ları ve ilk permission_required tanımını koru (satır 0-200 civarı)
    cleaned_lines = lines[:131]  # permission_required'dan önce
    
    # permission_required fonksiyonunu ekle (sadece bir kez)
    cleaned_lines.extend(lines[131:200])  # permission_required fonksiyonu
    
    # 4. Flask app tanımından itibaren devam et
    cleaned_lines.extend(lines[app_definitions[3]:])
    
    # Temizlenmiş dosyayı yaz
    with open('firstwebsite/app_cleaned.py', 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print(f"Cleaned file written to app_cleaned.py")
    print(f"Original: {len(lines)} lines")
    print(f"Cleaned: {len(cleaned_lines)} lines")
    print(f"Removed: {len(lines) - len(cleaned_lines)} duplicate lines")

if __name__ == '__main__':
    clean_app_file()
