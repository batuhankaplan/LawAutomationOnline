#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask uygulamasını ASCII-safe environment ile başlatma scripti
"""

import os
import sys

# Environment variables'daki Türkçe karakterleri temizle
def clean_environment():
    """Environment variables'daki Türkçe karakterleri temizle"""
    
    problematic_vars = ['HOSTNAME', 'COMPUTERNAME', 'LOGONSERVER', 'USERDOMAIN', 'USERDOMAIN_ROAMINGPROFILE']
    
    for var in problematic_vars:
        if var in os.environ:
            original_value = os.environ[var]
            # Türkçe karakterleri ASCII'ye çevir
            clean_value = original_value.replace('Ü', 'U').replace('ü', 'u').replace('Ğ', 'G').replace('ğ', 'g').replace('Ş', 'S').replace('ş', 's').replace('Ç', 'C').replace('ç', 'c').replace('İ', 'I').replace('ı', 'i').replace('Ö', 'O').replace('ö', 'o')
            os.environ[var] = clean_value
            print(f"Temizlendi: {var} = {clean_value}")

if __name__ == "__main__":
    print("Environment variables temizleniyor...")
    clean_environment()
    
    print("\nFlask uygulaması başlatılıyor...")
    
    # Flask uygulamasını import et ve başlat
    from app import app
    
    app.run(debug=True, host='127.0.0.1', port=5000)