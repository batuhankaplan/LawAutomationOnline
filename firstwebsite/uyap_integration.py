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

class UYAPIntegration:
    def __init__(self):
        # Chrome ayarlarını yapılandır
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--enable-automation')  # Otomasyonu etkinleştir
        chrome_options.add_argument('--no-sandbox')  # Sandbox modunu devre dışı bırak
        chrome_options.add_argument('--disable-dev-shm-usage')  # Paylaşılan bellek kullanımını devre dışı bırak
        chrome_options.add_experimental_option('useAutomationExtension', False)  # Otomasyon uzantısını devre dışı bırak
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Otomasyon bildirimini gizle
        
        # Chrome sürücüsünü başlat
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.base_url = "https://avukatbeta.uyap.gov.tr"
        
        # İşlenen birimleri takip etmek için sözlük
        self.islenen_birimler = {}
        
    def login(self):
        """
        UYAP Avukat Portalına giriş yapar
        Not: E-imza ile giriş yapılacağı için kullanıcının manuel olarak giriş yapması beklenir
        """
        try:
            self.driver.get(self.base_url)
            print("UYAP sayfası açıldı, e-imza ile giriş bekleniyor...")
            
            # E-imza ile giriş için yeterli süre tanı (60 saniye)
            time.sleep(60)
            
            # Giriş başarılı mı kontrol et - sol menüyü ara
            try:
                # Sol menüdeki Dosya Sorgulama İşlemleri'ni kontrol et
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dosya Sorgulama İşlemleri')]"))
                )
                print("Giriş başarılı!")
                return True
            except:
                print("Giriş başarısız - menü elemanları bulunamadı")
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
            # 1. Adım: Dosya Sorgulama İşlemleri menüsüne tıkla
            def click_dosya_sorgulama():
                print("\n1. Adım: Dosya Sorgulama İşlemleri menüsüne tıklanıyor...")
                dosya_sorgulama = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Dosya Sorgulama İşlemleri')]"))
                )
                self.driver.execute_script("arguments[0].click();", dosya_sorgulama)
                time.sleep(3)
                print("Dosya Sorgulama İşlemleri menüsüne tıklama başarılı")
            
            self.safe_action(click_dosya_sorgulama)

            # 2. Adım: Dosya Sorgula seçeneğine tıkla
            def click_dosya_sorgula():
                print("\n2. Adım: Dosya Sorgula seçeneğine tıklanıyor...")
                dosya_sorgula = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Dosya Sorgula')]"))
                )
                self.driver.execute_script("arguments[0].click();", dosya_sorgula)
                time.sleep(3)
                print("Dosya Sorgula seçeneğine tıklama başarılı")
            
            self.safe_action(click_dosya_sorgula)

            # Diğer adımlar için de aynı mantık...
            # Her işlem öncesi ve sonrası popup kontrolü yapılacak

            # Örnek olarak yargı türü seçimi:
            def select_yargi_turu(yargi_turu):
                print(f"\nYargı türü '{yargi_turu}' için işlem başlatılıyor...")
                inputs = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input.dx-texteditor-input"))
                )
                yargi_turu_input = inputs[0]
                yargi_turu_input.clear()
                yargi_turu_input.send_keys(yargi_turu)
                time.sleep(2)
                self.check_and_close_popup()  # Ara kontrol
                yargi_turu_input.send_keys(Keys.ENTER)
                time.sleep(2)
                print(f"'{yargi_turu}' seçildi")
            
            # Her yargı türü için işlem yap
            for yargi_turu in ["Ceza", "Hukuk", "İcra"]:
                self.safe_action(lambda: select_yargi_turu(yargi_turu))
                
                # Yargı birimi seçimi ve diğer işlemler...
                # Her kritik işlem için safe_action kullan
            
            return []

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