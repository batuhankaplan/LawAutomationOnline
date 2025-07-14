# -*- coding: utf-8 -*-
"""
Web arayüzü üzerinden e-posta test et
"""
import requests
import json

def test_email_via_web():
    """Web arayüzü üzerinden e-posta testi"""
    
    # Flask uygulamasının URL'i
    base_url = "http://127.0.0.1:5000"
    
    # Login sayfasından session cookie almak için
    session = requests.Session()
    
    print("🌐 Flask uygulamasına bağlanıyor...")
    
    try:
        # Ana sayfa isteği
        response = session.get(f"{base_url}/")
        print(f"📡 Ana sayfa: {response.status_code}")
        
        # Login sayfası isteği
        response = session.get(f"{base_url}/login")
        print(f"📡 Login sayfası: {response.status_code}")
        
        # Admin kullanıcısı ile giriş yapmayı dene
        login_data = {
            'email': 'admin@example.com',
            'password': 'admin123'
        }
        
        response = session.post(f"{base_url}/login", data=login_data)
        print(f"🔐 Login denemesi: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Giriş başarılı!")
            
            # E-posta test isteği gönder
            test_data = {
                'type': 'general'
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            print("📧 E-posta test isteği gönderiliyor...")
            response = session.post(
                f"{base_url}/test_email_notification", 
                json=test_data,
                headers=headers
            )
            
            print(f"📨 Test sonucu: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Başarılı: {result}")
            else:
                print(f"❌ Hata: {response.text}")
                
        else:
            print("❌ Giriş başarısız!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Flask uygulamasına bağlanamadı. Uygulama çalışıyor mu?")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    print("🚀 Web E-posta Test Başlıyor...\n")
    test_email_via_web()