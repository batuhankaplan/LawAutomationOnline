from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import json
from selenium.webdriver.common.keys import Keys
import os
import subprocess

class UYAPIntegration:
    def __init__(self):
        try:
            # Chrome ayarlarını yapılandır
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            debug_port = 9222
            
            # Mevcut Chrome profilini kullan
            user_data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data')
            
            # Chrome'u başlat
            subprocess.Popen([
                chrome_path,
                f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={user_data_dir}",
                "--profile-directory=Default",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized",
                "--disable-popup-blocking",
                "--disable-notifications",
                "--homepage=https://avukatbeta.uyap.gov.tr/giris"
            ])
            
            time.sleep(3)  # Chrome'un başlaması için bekle
            
            # Chrome'a bağlan
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
            chrome_options.add_argument("--start-maximized")
            
            # Chrome sürücüsünü başlat
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Doğrudan UYAP sayfasına git
            self.driver.get("https://avukatbeta.uyap.gov.tr/giris")
            print("Chrome başarıyla başlatıldı ve UYAP sayfasına yönlendirildi.")
            
        except Exception as e:
            print(f"Chrome başlatma hatası: {str(e)}")
            raise
        
        # İşlenen birimleri takip etmek için sözlük
        self.islenen_birimler = {}
        
    def login(self):
        """
        UYAP Avukat Portalına giriş yapar ve detaylı arama sayfasına gider
        Not: E-imza ile giriş yapılacağı için kullanıcının manuel olarak giriş yapması beklenir
        """
        try:
            # URL'yi kontrol et ve gerekirse düzelt
            current_url = self.driver.current_url
            if "avukatbeta.uyap.gov.tr" not in current_url:
                print(f"Yanlış sayfaya yönlendirildi: {current_url}")
                print("UYAP sayfasına yeniden yönlendiriliyor...")
                self.driver.get("https://avukatbeta.uyap.gov.tr")
                time.sleep(2)
            
            print("UYAP sayfası açıldı, e-imza ile giriş bekleniyor...")
            
            # Giriş başarılı olana kadar maksimum 30 saniye bekle
            max_wait = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    # Ana sayfadaki herhangi bir menü öğesini kontrol et
                    menu_item = WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "span.dx-menu-item-text"))
                    )
                    print("Giriş başarılı! Detaylı arama sayfasına yönlendiriliyor...")
                    break
                except:
                    time.sleep(1)  # 1 saniye bekle ve tekrar kontrol et
                    continue
            
            # Ana sayfadaki detaylı arama ikonuna tıkla
            try:
                # Detaylı arama ikonunu bul ve tıkla (pembe renkli kutu)
                detayli_arama = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.dx-box-item div.dx-box-item:nth-child(2)"))
                )
                detayli_arama.click()
                time.sleep(2)
                print("Detaylı arama sayfası açıldı!")
                return True
            except Exception as e:
                print(f"Detaylı arama sayfası açılamadı: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Giriş hatası: {str(e)}")
            return False

    def check_and_close_popup(self):
        """
        Video popup'ını kontrol eder ve varsa kapatır
        """
        try:
            # Video popup'ını bulmaya çalış (kısa timeout ile)
            video_popup = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.dx-popup-wrapper"))
            )
            
            # Kapatma butonunu bul ve tıkla
            close_button = video_popup.find_element(By.CSS_SELECTOR, "div.dx-closebutton")
            self.driver.execute_script("arguments[0].click();", close_button)
            print("Video popup'ı kapatıldı")
            time.sleep(1)
            return True
        except:
            return False

    def safe_action(self, action_func):
        """
        Herhangi bir işlemi yaparken popup kontrolü yapar
        """
        try:
            # İşlemi yap
            result = action_func()
            # Popup kontrolü
            self.check_and_close_popup()
            return result
        except Exception as e:
            # Hata durumunda da popup'ı kontrol et
            self.check_and_close_popup()
            raise e

    def get_case_files(self):
        """
        UYAP'tan dava dosyalarını çeker
        """
        try:
            print("\nDosyalar alınıyor...")
            
            # Dava Açılış İşlemleri menüsüne tıkla
            def click_dava_acilis():
                dava_acilis = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Dava Açılış İşlemleri')]"))
                )
                self.driver.execute_script("arguments[0].click();", dava_acilis)
                time.sleep(2)
                print("Dava Açılış İşlemleri menüsü açıldı")
            
            self.safe_action(click_dava_acilis)
            
            # Sık Kullanılan Dosyalarım'a tıkla
            def click_sik_kullanilanlar():
                sik_kullanilanlar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sık Kullanılan Dosyalarım')]"))
                )
                self.driver.execute_script("arguments[0].click();", sik_kullanilanlar)
                time.sleep(2)
                print("Sık Kullanılan Dosyalarım sayfası açıldı")
            
            self.safe_action(click_sik_kullanilanlar)
            
            # Sonuçları kaydet
            def save_results():
                try:
                    # Tablo elementini bul
                    table = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.dx-datagrid-content table"))
                    )
                    
                    # Tüm satırları al
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    dosyalar = []
                    
                    for row in rows[1:]:  # Başlık satırını atla
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 4:  # Sık kullanılanlar tablosunda genelde 4 sütun var
                                dosya = {
                                    'dosya_no': cells[0].text.strip(),
                                    'mahkeme': cells[1].text.strip(),
                                    'taraflar': cells[2].text.strip(),
                                    'durum': cells[3].text.strip() if len(cells) > 3 else 'Aktif'
                                }
                                print(f"Dosya bulundu: {dosya['dosya_no']}")
                                dosyalar.append(dosya)
                        except Exception as e:
                            print(f"Satır okuma hatası: {str(e)}")
                            continue
                    
                    return dosyalar
                    
                except Exception as e:
                    print(f"Tablo okuma hatası: {str(e)}")
                    return []
            
            return self.safe_action(save_results)
            
        except Exception as e:
            print(f"Dosya çekme işleminde beklenmeyen hata: {str(e)}")
            return []

    def get_case_details(self, dosya_no):
        """
        Belirli bir dosyanın detaylarını çeker
        """
        try:
            # Dosya detaylarına git
            dosya_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//td[contains(text(), '{dosya_no}')]//ancestor::tr//a[contains(@title, 'Detay')]"))
            )
            dosya_link.click()
            time.sleep(2)  # Detayların yüklenmesi için bekle

            # Detay bilgilerini topla
            details = {
                'dosya_no': dosya_no,
                'mahkeme': self._get_element_text("//td[contains(text(), 'Mahkeme')]/following-sibling::td"),
                'taraflar': self._get_element_text("//td[contains(text(), 'Taraflar')]/following-sibling::td"),
                'durusma_tarihi': self._get_element_text("//td[contains(text(), 'Duruşma')]/following-sibling::td"),
                'son_islem': self._get_element_text("//td[contains(text(), 'Son İşlem')]/following-sibling::td"),
                'karar': self._get_element_text("//td[contains(text(), 'Karar')]/following-sibling::td")
            }

            # Önceki sayfaya dön
            self.driver.back()
            time.sleep(1)

            return details

        except Exception as e:
            print(f"Dosya detayları çekme hatası: {str(e)}")
            return None

    def _get_element_text(self, xpath, timeout=5):
        """
        Belirtilen XPath'teki elementin metnini alır
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element.text.strip()
        except:
            return ""

    def close(self):
        """
        Tarayıcıyı kapatır
        """
        if self.driver:
            self.driver.quit() 

    def birim_islendi(self, yargi_turu, birim_adi):
        """
        Belirtilen yargı türü ve birim kombinasyonunun daha önce işlenip işlenmediğini kontrol eder
        """
        if yargi_turu not in self.islenen_birimler:
            return False
        return birim_adi in self.islenen_birimler[yargi_turu]
        
    def birim_islendi_olarak_isaretle(self, yargi_turu, birim_adi):
        """
        Belirtilen yargı türü ve birimi işlenmiş olarak işaretler
        """
        if yargi_turu not in self.islenen_birimler:
            self.islenen_birimler[yargi_turu] = set()
        self.islenen_birimler[yargi_turu].add(birim_adi)
        
    def sonuclari_kaydet(self, yargi_turu, birim_adi):
        """
        Sorgu sonuçlarını veritabanına kaydeder
        """
        try:
            # Sonuç tablosunu bul
            tablo = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.dx-datagrid-table"))
            )
            
            # Tablo satırlarını al
            satirlar = tablo.find_elements(By.TAG_NAME, "tr")
            
            for satir in satirlar[1:]:  # İlk satır başlık olduğu için atla
                try:
                    # Sütunları al
                    sutunlar = satir.find_elements(By.TAG_NAME, "td")
                    if len(sutunlar) >= 6:
                        dosya = {
                            'dosya_no': sutunlar[1].text.strip(),
                            'mahkeme': sutunlar[2].text.strip(),
                            'taraflar': sutunlar[3].text.strip(),
                            'durum': 'Aktif',
                            'son_islem': sutunlar[4].text.strip(),
                            'son_islem_tarihi': sutunlar[5].text.strip(),
                            'yargi_turu': yargi_turu,
                            'yargi_birimi': birim_adi
                        }
                        print(f"Dosya bulundu: {dosya['dosya_no']}")
                        # TODO: Burada dosyayı veritabanına kaydet
                        
                except Exception as e:
                    print(f"Satır işlenirken hata: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Sonuçlar kaydedilirken hata: {str(e)}")
            return 

    def search_files(self, yargi_turu="Ceza"):
        """
        Dosya sorgulama işlemini gerçekleştirir
        """
        try:
            print(f"{yargi_turu} türü için dosya sorgulaması başlatılıyor...")
            
            # Ana sayfaya git
            self.driver.get("https://avukatbeta.uyap.gov.tr")
            time.sleep(2)
            
            # Detaylı Arama butonunu bul ve tıkla
            detayli_arama = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.dx-box-item button[title='Detaylı Arama']"))
            )
            detayli_arama.click()
            time.sleep(2)
            
            # Yargı türü seçim kutusunu bul
            yargi_turu_dropdown = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class*='yargiTuru']"))
            )
            yargi_turu_dropdown.click()
            time.sleep(1)
            
            # Yargı türünü seç
            yargi_turu_secim = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'dx-item-content') and contains(text(), '{yargi_turu}')]"))
            )
            yargi_turu_secim.click()
            time.sleep(1)
            
            # Sorgula butonunu bul ve tıkla
            sorgula_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.dx-button-content:has(span:contains('Sorgula'))"))
            )
            sorgula_button.click()
            
            print(f"{yargi_turu} türündeki dosyalar sorgulanıyor...")
            time.sleep(5)  # Sonuçların yüklenmesi için bekle
            
            # Sonuçları kaydet
            try:
                # Tablo elementini bul
                table = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.dx-datagrid-content table"))
                )
                
                # Tüm satırları al
                rows = table.find_elements(By.TAG_NAME, "tr")
                dosyalar = []
                
                for row in rows[1:]:  # Başlık satırını atla
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 4:
                            dosya = {
                                'dosya_no': cells[0].text.strip(),
                                'mahkeme': cells[1].text.strip(),
                                'taraflar': cells[2].text.strip(),
                                'durum': cells[3].text.strip() if len(cells) > 3 else 'Aktif',
                                'dosya_turu': yargi_turu
                            }
                            print(f"Dosya bulundu: {dosya['dosya_no']} ({yargi_turu})")
                            dosyalar.append(dosya)
                    except Exception as e:
                        print(f"Satır okuma hatası: {str(e)}")
                        continue
                
                return dosyalar
                
            except Exception as e:
                print(f"Tablo okuma hatası: {str(e)}")
                return []
            
        except Exception as e:
            print(f"Dosya sorgulama hatası: {str(e)}")
            return [] 