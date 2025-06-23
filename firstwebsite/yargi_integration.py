"""
Unified Yargi Integration - Tüm yargı sistemi MCP'lerini birleştiren ana entegrasyon dosyası
Bu dosya artık unified_mcp_modules.py dosyasından import yapar
"""

# Yeni birleşik dosyadan import (absolute import)
from unified_mcp_modules import (
    # Anayasa
    AnayasaMahkemesiApiClient,
    AnayasaNormDenetimiSearchRequest,
    AnayasaSearchResult,
    AnayasaDocumentMarkdown,
    AnayasaBireyselReportSearchRequest,
    AnayasaBireyselReportSearchResult,
    AnayasaBireyselBasvuruDocumentMarkdown,
    
    # Danıştay
    DanistayApiClient,
    DanistayKeywordSearchRequest,
    DanistayDetailedSearchRequest,
    DanistayApiResponse,
    DanistayDocumentMarkdown,
    
    # Emsal
    EmsalApiClient,
    EmsalSearchRequest,
    EmsalApiResponse,
    EmsalDocumentMarkdown,
    
    # KIK
    KikApiClient,
    KikSearchRequest,
    KikSearchResult,
    KikDocumentMarkdown,
    KikKararTipi,
    
    # Rekabet
    RekabetKurumuApiClient,
    RekabetKurumuSearchRequest,
    RekabetSearchResult,
    RekabetDocument,
    
    # Uyuşmazlık
    UyusmazlikApiClient,
    UyusmazlikSearchRequest,
    UyusmazlikSearchResponse,
    UyusmazlikDocumentMarkdown,
    
    # Yargıtay
    YargitayOfficialApiClient,
    YargitayDetailedSearchRequest,
    YargitayApiSearchResponse,
    YargitayDocumentMarkdown,
    
    # Logging
    logger
)

import asyncio
import logging
import requests
import os
import tempfile
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup
import time
import html
import json

# MCP modülleri artık unified_mcp_modules'tan import ediliyor
# Eski import'lar kaldırıldı

logger = logging.getLogger(__name__)

@dataclass
class YargiSearchResult:
    """Flask için uyumlu arama sonuç veri yapısı"""
    id: str
    title: str
    court: str
    decision_date: str
    case_number: str
    decision_number: str
    summary: str = ""
    document_url: str = ""

@dataclass
class YargiSearchResponse:
    """Flask için uyumlu arama yanıt veri yapısı"""
    results: List[YargiSearchResult]
    total_records: int
    current_page: int
    page_size: int
    total_pages: int

# HTTP istekleri için yardımcı sınıf
class HttpRequestManager:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_content(self, url, timeout=30):
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"HTTP isteği hatası: {e}")
            return None
    
    def get_content_with_different_agents(self, url, timeout=30):
        """Farklı user agent'lar ile deneme yapar"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59'
        ]
        
        for i, agent in enumerate(user_agents):
            try:
                headers = self.session.headers.copy()
                headers['User-Agent'] = agent
                
                response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    logger.info(f"Başarılı istek - User Agent {i+1}")
                    return response
                else:
                    logger.warning(f"User Agent {i+1} başarısız: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"User Agent {i+1} hatası: {e}")
                continue
        
        return None
    
    def get_content_with_session_retry(self, url, timeout=30, max_retries=3):
        """Session yenileme ile retry yapar"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Session'ı yenile
                    self.session.close()
                    self.session = requests.Session()
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    })
                
                response = self.session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                return response
                
            except Exception as e:
                logger.warning(f"Retry attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)  # 2 saniye bekle
        
        return None

# Global HTTP istek yöneticisi
http_manager = HttpRequestManager()

class YargiFlaskIntegration:
    """Yargı MCP modüllerini Flask ile entegre eden ana sınıf"""
    
    def __init__(self):
        self.yargitay_client = YargitayOfficialApiClient()
        self.danistay_client = DanistayApiClient()
        self.emsal_client = EmsalApiClient()
        self.anayasa_client = AnayasaMahkemesiApiClient()
        self.uyusmazlik_client = UyusmazlikApiClient()
        self.kik_client = KikApiClient()
        self.rekabet_client = RekabetKurumuApiClient()
        self.http_manager = http_manager
    
    def search_all_courts(self, 
                         keyword: str,
                         court_type: str = "all",
                         court_unit: str = "",
                         case_year: str = "",
                         decision_year: str = "",
                         start_date: str = "",
                         end_date: str = "",
                         page_number: int = 1,
                         page_size: int = 20) -> Dict[str, Any]:
        """Tüm mahkemelerde arama yapar"""
        
        results = {
            'yargitay': {'count': 0, 'decisions': []},
            'danistay': {'count': 0, 'decisions': []},
            'emsal': {'count': 0, 'decisions': []},
            'anayasa': {'count': 0, 'decisions': []},
            'uyusmazlik': {'count': 0, 'decisions': []},
            'kik': {'count': 0, 'decisions': []},
            'rekabet': {'count': 0, 'decisions': []},
            'total_count': 0,
            'pagination': {
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': 1,
                'total_records': 0
            }
        }
        
        try:
            # Asyncio event loop oluştur
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Yargıtay araması
            if court_type in ["all", "yargitay"]:
                try:
                    yargitay_result = loop.run_until_complete(
                        self._search_yargitay(
                            keyword=keyword,
                            court_unit=court_unit,
                            case_year=case_year,
                            decision_year=decision_year,
                            start_date=start_date,
                            end_date=end_date,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['yargitay'] = yargitay_result
                    logger.info(f"Yargıtay araması tamamlandı: {len(yargitay_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Yargıtay arama hatası: {e}")
                    results['yargitay'] = self._empty_response(page_number, page_size)
            
            # Danıştay araması
            if court_type in ["all", "danistay"]:
                try:
                    danistay_result = loop.run_until_complete(
                        self._search_danistay(
                            keyword=keyword,
                            court_unit=court_unit,
                            case_year=case_year,
                            decision_year=decision_year,
                            start_date=start_date,
                            end_date=end_date,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['danistay'] = danistay_result
                    logger.info(f"Danıştay araması tamamlandı: {len(danistay_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Danıştay arama hatası: {e}")
                    results['danistay'] = self._empty_response(page_number, page_size)
            
            # Emsal araması
            if court_type in ["all", "emsal"]:
                try:
                    emsal_result = loop.run_until_complete(
                        self._search_emsal(
                            keyword=keyword,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['emsal'] = emsal_result
                    logger.info(f"Emsal araması tamamlandı: {len(emsal_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Emsal arama hatası: {e}")
                    results['emsal'] = self._empty_response(page_number, page_size)
            
            # Anayasa Mahkemesi araması
            if court_type in ["all", "anayasa"]:
                try:
                    anayasa_result = loop.run_until_complete(
                        self._search_anayasa(
                            keyword=keyword,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['anayasa'] = anayasa_result
                    logger.info(f"Anayasa Mahkemesi araması tamamlandı: {len(anayasa_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Anayasa Mahkemesi arama hatası: {e}")
                    results['anayasa'] = self._empty_response(page_number, page_size)
            
            # Uyuşmazlık Mahkemesi araması
            if court_type in ["all", "uyusmazlik"]:
                try:
                    uyusmazlik_result = loop.run_until_complete(
                        self._search_uyusmazlik(
                            keyword=keyword,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['uyusmazlik'] = uyusmazlik_result
                    logger.info(f"Uyuşmazlık Mahkemesi araması tamamlandı: {len(uyusmazlik_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Uyuşmazlık Mahkemesi arama hatası: {e}")
                    results['uyusmazlik'] = self._empty_response(page_number, page_size)
            
            # KİK araması
            if court_type in ["all", "kik"]:
                try:
                    kik_result = loop.run_until_complete(
                        self._search_kik(
                            keyword=keyword,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['kik'] = kik_result
                    logger.info(f"KİK araması tamamlandı: {len(kik_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"KİK arama hatası: {e}")
                    results['kik'] = self._empty_response(page_number, page_size)
            
            # Rekabet Kurumu araması
            if court_type in ["all", "rekabet"]:
                try:
                    rekabet_result = loop.run_until_complete(
                        self._search_rekabet(
                            keyword=keyword,
                            page_number=page_number,
                            page_size=page_size
                        )
                    )
                    results['rekabet'] = rekabet_result
                    logger.info(f"Rekabet Kurumu araması tamamlandı: {len(rekabet_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Rekabet Kurumu arama hatası: {e}")
                    results['rekabet'] = self._empty_response(page_number, page_size)
                
        except Exception as e:
            logger.error(f"Genel arama hatası: {e}")
            # Hata durumunda boş sonuç döndür
            for ct in (["all"] if court_type == "all" else [court_type]):
                results[ct] = self._empty_response(page_number, page_size)
        
        # Toplam sonuç sayısını hesapla
        total_count = sum([
            results['yargitay']['count'],
            results['danistay']['count'],
            results['emsal']['count'],
            results['anayasa']['count'],
            results['uyusmazlik']['count'],
            results['kik']['count'],
            results['rekabet']['count']
        ])
        
        results['total_count'] = total_count
        
        # Sayfalama bilgilerini güncelle
        results['pagination']['total_records'] = total_count
        if total_count > 0:
            results['pagination']['total_pages'] = max(1, (total_count + page_size - 1) // page_size)
        
        return results
    
    def _clean_decision_text(self, text: str) -> str:
        """Karar metnini temizle ve düzenle - geliştirilmiş versiyon"""
        if not text:
            return ""
        
        import re
        
        # HTML entity'leri decode et
        text = html.unescape(text)
        
        # Gereksiz HTML taglerini temizle (eğer varsa)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Çoklu satır sonlarını normalize et
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Satırları işle
        lines = text.split('\n')
        cleaned_lines = []
        
        # Gereksiz satırları filtrele
        skip_patterns = [
            r'^(ana sayfa|menü|giriş|çıkış|login|logout).*$',
            r'^(copyright|©|tüm hakları).*$',
            r'^(javascript|cookie|çerez).*$',
            r'^(sayfa|page)\s*\d+.*$',
            r'^(http|www\.|ftp).*$',
            r'^\s*[\d\.\-\s]+$',  # Sadece sayı ve nokta içeren satırlar
            r'^.{1,10}$',  # Çok kısa satırlar (10 karakter altı)
            r'^(.*menü.*|.*navigation.*|.*footer.*|.*header.*)$',
            r'^(.*bilgi bankası.*|.*uyap.*|.*yargıtay.*|.*danıştay.*)(?!.*karar).*$'  # Site adları ama karar içermeyen
        ]
        
        for line in lines:
            line = line.strip()
            
            # Boş satırları atla
            if not line:
                continue
                
            # Skip pattern'leri kontrol et
            should_skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break
            
            if not should_skip:
                # Karar metni için pozitif göstergeler
                positive_indicators = [
                    'karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'esas', 'sonuç', 
                    'davacı', 'davalı', 'başvuran', 'müdahil', 'temyiz', 'istinaf',
                    'dosya', 'duruşma', 'delil', 'tanık', 'bilirkişi', 'keşif',
                    'hukuki', 'kanun', 'madde', 'fıkra', 'bent', 'yönetmelik',
                    'tebliğ', 'icra', 'infaz', 'takip', 'haciz', 'satış'
                ]
                
                # Eğer satır yeterince uzunsa veya pozitif gösterge içeriyorsa ekle
                if len(line) > 15 or any(indicator in line.lower() for indicator in positive_indicators):
                    cleaned_lines.append(line)
        
        # Temizlenmiş satırları birleştir
        text = '\n'.join(cleaned_lines)
        
        # Tekrarlayan cümleleri temizle
        sentences = text.split('.')
        unique_sentences = []
        seen_sentences = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Çok kısa cümleleri atla
                sentence_normalized = re.sub(r'\s+', ' ', sentence.lower())
                if sentence_normalized not in seen_sentences:
                    seen_sentences.add(sentence_normalized)
                    unique_sentences.append(sentence)
        
        text = '. '.join(unique_sentences)
        
        # Özel karakterleri normalize et
        text = re.sub(r'[""''‚„]', '"', text)  # Tırnak işaretlerini normalize et
        text = re.sub(r'[–—]', '-', text)  # Tire işaretlerini normalize et
        
        # Son temizlik
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Eğer metin çok kısaysa ve sadece navigasyon içeriyorsa boş döndür
        if len(text) < 100:
            navigation_words = ['menü', 'sayfa', 'giriş', 'çıkış', 'ana sayfa', 'javascript', 'cookie']
            if any(word in text.lower() for word in navigation_words):
                return ""
        
        return text
    
    def _clean_decision_text_light(self, text: str) -> str:
        """Karar metnini hafif temizle - daha az agresif filtreleme"""
        if not text:
            return ""
        
        import re
        
        # Orijinal metin uzunluğunu kaydet
        original_length = len(text)
        
        # HTML entity'leri decode et
        text = html.unescape(text)
        
        # Gereksiz HTML taglerini temizle (eğer varsa)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Çoklu satır sonlarını normalize et
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Eğer metin çok uzun ise (5000+ karakter) filtreleme yap, yoksa minimal işlem
        if original_length > 5000:
            # Satırları işle - sadece çok kısa satırları filtrele
            lines = text.split('\n')
            cleaned_lines = []
            
            # Sadece çok gereksiz satırları filtrele
            skip_patterns = [
                r'^(javascript|cookie|çerez).*$',
                r'^(http|www\.|ftp).*$',
                r'^\s*[\d\.\-\s]{1,5}$',  # Sadece çok kısa sayı dizileri
                r'^.{1,3}$'  # Çok kısa satırlar (3 karakter altı)
            ]
            
            for line in lines:
                line = line.strip()
                
                # Boş satırları atla
                if not line:
                    continue
                    
                # Sadece gerçekten gereksiz olan satırları skip et
                should_skip = False
                for pattern in skip_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        should_skip = True
                        break
                
                if not should_skip:
                    cleaned_lines.append(line)
            
            # Temizlenmiş satırları birleştir
            text = '\n'.join(cleaned_lines)
        
        # Özel karakterleri normalize et
        text = re.sub(r'[""''‚„]', '"', text)  # Tırnak işaretlerini normalize et
        text = re.sub(r'[–—]', '-', text)  # Tire işaretlerini normalize et
        
        # Son temizlik
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Eğer temizleme sonucu metin çok kısaldıysa ve orijinal uzunsa, daha az agresif temizle
        if len(text) < 100 and original_length > 1000:
            # Minimal temizlik yap
            text = html.unescape(text) if text else ""
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _empty_response(self, page_number: int, page_size: int) -> Dict[str, Any]:
        """Boş yanıt döndürür"""
        return {
            'decisions': [],
            'count': 0,
            'current_page': page_number,
            'page_size': page_size,
            'total_pages': 0
        }
    
    async def _search_yargitay(self,
                              keyword: str,
                              court_unit: str = "",
                              case_year: str = "",
                              decision_year: str = "",
                              start_date: str = "",
                              end_date: str = "",
                              page_number: int = 1,
                              page_size: int = 20) -> Dict[str, Any]:
        """Yargıtay arama yapar - önce API'yi dener, başarısızsa web scraping kullanır"""
        
        try:
            # Yargıtay arama parametrelerini hazırla
            search_request = YargitayDetailedSearchRequest(
                arananKelime=keyword if keyword else "",
                birimYrgHukukDaire=court_unit if court_unit else "",
                esasYil=case_year if case_year else "",
                kararYil=decision_year if decision_year else "",
                baslangicTarihi=start_date if start_date else "",
                bitisTarihi=end_date if end_date else "",
                pageNumber=page_number,
                pageSize=page_size
            )
            
            logger.info(f"Yargıtay API arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.yargitay_client.search_detailed_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.data and api_response.data.data:
                for decision in api_response.data.data:
                    flask_result = YargiSearchResult(
                        id=decision.id,
                        title=f"Yargıtay {decision.daire or ''} - {decision.kararNo or ''}",
                        court=decision.daire or "Yargıtay",
                        decision_date=decision.kararTarihi or "",
                        case_number=decision.esasNo or "",
                        decision_number=decision.kararNo or "",
                        summary=f"Yargıtay kararı: {keyword}"[:200],
                        document_url=f"https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/pf/bilgi-bankasi-detay.xhtml?id={decision.id}"
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.data.recordsTotal if api_response.data else 0
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"Yargıtay API başarılı: {len(flask_results)} sonuç")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.warning(f"Yargıtay API hatası: {e}")
            logger.info("Yargıtay web scraping deneniyor...")
            # API başarısız, web scraping'e geç
            return await self._search_yargitay_web_scraping(keyword, page_number, page_size)

    async def _search_yargitay_web_scraping(self, keyword: str, page_number: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Yargıtay web scraping ile gerçek arama yapar"""
        try:
            logger.info(f"Yargıtay web scraping başlıyor: {keyword}")
            
            # Gerçek Yargıtay web scraping yapalım
            logger.info("Yargıtay gerçek web scraping başlatılıyor...")
            
            # Türkiye'den erişilebilir gerçek Yargıtay URL'leri
            search_urls = [
                f"https://www.yargitay.gov.tr/kararlar/arama?q={keyword}",
                f"https://yargitaykararlari.com/arama/{keyword}",
                f"https://karararama.yargitay.gov.tr/",  # Ana sayfa + form post
                f"https://www.yargitay.gov.tr/kategori/4",  # Kararlar sayfası
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            for url in search_urls:
                try:
                    logger.info(f"Yargıtay URL test edilyor: {url}")
                    response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                        
                        # Yargıtay için çoklu selector stratejisi
                        selectors = [
                            'table.table tbody tr',  # Bootstrap table rows
                            'div.karar-item',  # Karar item divleri
                            'div.result-item', # Sonuç item divleri
                            'tr[onclick*="karar"]',  # Onclick eventi olan karar satırları
                            'a[href*="karar"]',  # Karar linklerini içeren a tagları
                            'div[class*="karar"]',  # Karar içeren class'lı divler
                            'li.list-group-item',  # List group items
                            'div.card-body',  # Card body divleri
                            'table tr td',  # Genel table satırları
                        ]
                        
                        flask_results = []
                        for selector in selectors:
                            elements = soup.select(selector)
                            
                            if elements and len(elements) >= 3:
                                logger.info(f"Yargıtay: {len(elements)} element bulundu ({selector})")
                                
                                for i, element in enumerate(elements[:page_size]):
                                    text = element.get_text(' ', strip=True)
                                    
                                    # Anlamlı içerik kontrolü
                                    if len(text) < 20:
                                        continue
                                        
                                    # Yargıtay spesifik bilgi çıkarma
                                    court = "Yargıtay"
                                    
                                    # Daire bilgisi çıkarma
                                    daire_patterns = [
                                        r'(\d+\.?\s*(?:hukuk|ceza|özel)\s*daire(?:si)?)',
                                        r'(hukuk\s*genel\s*kurulu?)',
                                        r'(ceza\s*genel\s*kurulu?)',
                                        r'(\d+\.\s*daire)',
                                    ]
                                    
                                    for pattern in daire_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            court = f"Yargıtay {match.group(1)}"
                                            break
                                    
                                    # Esas No çıkarma
                                    esas_patterns = [
                                        r'(?:esas|e\.?)\s*:?\s*(\d{4}/\d+)',
                                        r'(\d{4}/\d+)',  # Basit format
                                    ]
                                    esas_no = ""
                                    for pattern in esas_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            esas_no = match.group(1)
                                            break
                                    
                                    # Karar No çıkarma
                                    karar_patterns = [
                                        r'(?:karar|k\.?)\s*:?\s*(\d{4}/\d+)',
                                        r'k\.\s*(\d{4}/\d+)',
                                    ]
                                    karar_no = ""
                                    for pattern in karar_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            karar_no = match.group(1)
                                            break
                                    
                                    # Tarih çıkarma
                                    date_patterns = [
                                        r'(\d{1,2}[./]\d{1,2}[./]\d{4})',
                                        r'(\d{4}-\d{2}-\d{2})',
                                        r'(\d{1,2}\s+(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+\d{4})',
                                    ]
                                    decision_date = ""
                                    for pattern in date_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            decision_date = match.group(1)
                                            break
                                    
                                    # Link bulma
                                    doc_url = ""
                                    link_elem = element.find('a', href=True)
                                    if link_elem:
                                        doc_url = link_elem['href']
                                        if not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                    elif element.get('onclick'):
                                        # onclick eventi varsa URL çıkar
                                        onclick = element.get('onclick', '')
                                        url_match = re.search(r"(?:window\.open|location\.href)\s*=?\s*['\"]([^'\"]+)['\"]", onclick)
                                        if url_match:
                                            doc_url = url_match.group(1)
                                            if not doc_url.startswith('http'):
                                                doc_url = urljoin(url, doc_url)
                                    
                                    # Sonuç oluştur
                                    result_id = f"yargitay_real_{i+1}_{page_number}"
                                    title = f"{court} - {karar_no or esas_no or 'Karar'}"
                                    
                                    flask_result = YargiSearchResult(
                                        id=result_id,
                                        title=title,
                                        court=court,
                                        decision_date=decision_date,
                                        case_number=esas_no,
                                        decision_number=karar_no,
                                        summary=f"Yargıtay kararı: {keyword} - {text[:150]}...",
                                        document_url=doc_url or f"https://www.yargitay.gov.tr/kategori/4/{result_id}"
                                    )
                                    flask_results.append(flask_result)
                                    
                                    if len(flask_results) >= page_size:
                                        break
                                
                                if flask_results:
                                    logger.info(f"Yargıtay gerçek web scraping başarılı: {len(flask_results)} sonuç")
                                    return {
                                        'decisions': flask_results,
                                        'count': len(flask_results) * 2,  # Tahmin edilen toplam
                                        'current_page': page_number,
                                        'page_size': page_size,
                                        'total_pages': 2
                                    }
                                break
                                
                    else:
                        logger.warning(f"Yargıtay URL başarısız: {url} - {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"Yargıtay URL hatası ({url}): {e}")
                    continue
            
            # Hiçbir URL çalışmadı - fallback demo
            logger.warning("Yargıtay: Tüm URL'ler başarısız, minimal fallback")
            
            # Son çare olarak basit demo sonuç döndür
            fallback_result = YargiSearchResult(
                id=f"yargitay_fallback_{page_number}",
                title=f"Yargıtay Kararı - '{keyword}'",
                court="Yargıtay",
                decision_date="",
                case_number="",
                decision_number="",
                summary=f"'{keyword}' arama sonucu - Gerçek web sitesinden erişim sağlanamadı",
                document_url="https://www.yargitay.gov.tr/kategori/4"
            )
            
            return {
                'decisions': [fallback_result],
                'count': 1,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': 1
            }

                
        except Exception as e:
            logger.error(f"Yargıtay web scraping hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_danistay(self,
                              keyword: str,
                              court_unit: str = "",
                              case_year: str = "",
                              decision_year: str = "",
                              start_date: str = "",
                              end_date: str = "",
                              page_number: int = 1,
                              page_size: int = 20) -> Dict[str, Any]:
        """Danıştay API'sinde arama yapar - hızlı ve güvenilir"""
        
        try:
            # Danıştay arama parametrelerini hazırla
            keywords = [keyword] if keyword else []
            search_request = DanistayKeywordSearchRequest(
                andKelimeler=keywords,
                orKelimeler=[],
                notAndKelimeler=[],
                notOrKelimeler=[],
                pageNumber=page_number,
                pageSize=page_size
            )
            
            logger.info(f"Danıştay API arama yapılıyor: {keyword}")
            
            # Arama kelimesini global değişkende sakla (modal için)
            get_document_content._last_danistay_keyword = keyword
            
            # API çağrısı yap
            api_response = await self.danistay_client.search_keyword_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.data and api_response.data.data:
                for decision in api_response.data.data:
                    # chamber özelliğini güvenli şekilde al
                    chamber = getattr(decision, 'chamber', None) or getattr(decision, 'daire', None) or "Danıştay"
                    decision_id = getattr(decision, 'id', None) or f'DT_{page_number}_{len(flask_results)+1}'
                    karar_no = getattr(decision, 'kararNo', None) or getattr(decision, 'karar_no', '') or ""
                    karar_tarihi = getattr(decision, 'kararTarihi', None) or getattr(decision, 'karar_tarihi', '') or ""
                    esas_no = getattr(decision, 'esasNo', None) or getattr(decision, 'esas_no', '') or ""
                    
                    flask_result = YargiSearchResult(
                        id=str(decision_id),
                        title=f"Danıştay {chamber} - {karar_no}",
                        court=f"Danıştay {chamber}",
                        decision_date=karar_tarihi,
                        case_number=esas_no,
                        decision_number=karar_no,
                        summary=f"Danıştay kararı: {keyword}"[:200],
                        document_url=f"https://karararama.danistay.gov.tr/Karar/Detay/{decision_id}"
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.data.recordsTotal if api_response.data else 0
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"Danıştay API başarılı: {len(flask_results)} sonuç")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Danıştay arama hatası: {e}")
            
            # API başarısız, hızlı web scraping dene
            try:
                logger.info("Danıştay hızlı web scraping deneniyor...")
                
                # Gerçek Danıştay URL'leri - çoklu strateji
                quick_urls = [
                    f"https://www.danistay.gov.tr/TR/Dava-Arama?q={keyword}",
                    f"https://www.danistay.gov.tr/Kararlar/Arama?kelime={keyword}",
                    f"https://karararama.danistay.gov.tr/arama?q={keyword}",
                    f"https://www.danistay.gov.tr/",  # Ana sayfa
                    f"https://danistay.uyap.gov.tr/kararlar"  # UYAP entegrasyonu
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Connection': 'keep-alive',
                }
                
                for url in quick_urls:
                    try:
                        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Hızlı sonuç bulma - Danıştay spesifik selectorlar
                            quick_selectors = [
                                'tr[class*="karar"]', 'div[class*="karar"]',
                                '.karar-item', '.result-item', 'tr td',
                                'div[class*="decision"]', 'li[class*="result"]',
                                'table tr', 'tbody tr', 'tr[onclick]'  # Danıştay genelde onclick eventi olan tr'ler kullanır
                            ]
                            
                            flask_results = []
                            for selector in quick_selectors:
                                elements = soup.select(selector)
                                if elements and len(elements) >= 3:
                                    for i, element in enumerate(elements[:page_size]):
                                        title = element.get_text(strip=True)[:100] or f"Danıştay Kararı {i+1}"
                                        
                                        # Danıştay için özel link bulma
                                        link_elem = element.find('a')
                                        if not link_elem and element.get('onclick'):
                                            # onclick eventi varsa URL'yi oradan çıkar
                                            onclick = element.get('onclick', '')
                                            import re
                                            url_match = re.search(r"window\.open\('([^']+)'", onclick)
                                            if url_match:
                                                doc_url = url_match.group(1)
                                            else:
                                                doc_url = ''
                                        else:
                                            doc_url = link_elem.get('href', '') if link_elem else ''
                                        
                                        if doc_url and not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                        
                                        result_id = f"danistay_{i+1}_{page_number}"
                                        flask_result = YargiSearchResult(
                                            id=result_id,
                                            title=title,
                                            court="Danıştay",
                                            decision_date="",
                                            case_number="",
                                            decision_number="",
                                            summary=f"Danıştay kararı: {keyword}",
                                            document_url=doc_url or f"https://www.danistay.gov.tr/Karar/Detay/{result_id}"
                                        )
                                        flask_results.append(flask_result)
                                    
                                    if flask_results:
                                        logger.info(f"Danıştay hızlı scraping başarılı: {len(flask_results)} sonuç")
                                        return {
                                            'decisions': flask_results,
                                            'count': len(flask_results),
                                            'current_page': page_number,
                                            'page_size': page_size,
                                            'total_pages': 1
                                        }
                                    break
                                    
                    except Exception as url_error:
                        logger.warning(f"Danıştay hızlı URL hatası: {url_error}")
                        continue
                        
            except Exception as scraping_error:
                logger.warning(f"Danıştay web scraping hatası: {scraping_error}")
            
            return self._empty_response(page_number, page_size)
    
    async def _search_emsal(self,
                           keyword: str,
                           page_number: int = 1,
                           page_size: int = 20) -> Dict[str, Any]:
        """Emsal arama yapar - önce API'yi dener, başarısızsa web scraping kullanır"""
        
        try:
            # Emsal arama parametrelerini hazırla
            search_request = EmsalSearchRequest(
                keyword=keyword if keyword else "",
                page_number=page_number,
                page_size=page_size
            )
            
            logger.info(f"Emsal API arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.emsal_client.search_detailed_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.data and api_response.data.data:
                for decision in api_response.data.data:
                    flask_result = YargiSearchResult(
                        id=decision.id,
                        title=f"{decision.daire or 'UYAP Emsal'} - {decision.kararNo or ''}",
                        court=decision.daire or "UYAP Emsal",
                        decision_date=decision.kararTarihi or "",
                        case_number=decision.esasNo or "",
                        decision_number=decision.kararNo or "",
                        summary=f"Emsal kararı: {keyword}"[:200],
                        document_url=f"https://emsal.uyap.gov.tr/Karar/Detay/{decision.id}"
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.data.recordsTotal if api_response.data else 0
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"Emsal API başarılı: {len(flask_results)} sonuç")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.warning(f"Emsal API hatası: {e}")
            logger.info("Emsal web scraping deneniyor...")
            # API başarısız, web scraping'e geç
            return await self._search_emsal_web_scraping(keyword, page_number, page_size)

    async def _search_emsal_web_scraping(self, keyword: str, page_number: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Emsal UYAP için gerçek web scraping yapar"""
        try:
            logger.info(f"Emsal web scraping başlıyor: {keyword}")
            
            # Gerçek Emsal UYAP web scraping yapalım
            logger.info("Emsal UYAP gerçek web scraping başlatılıyor...")
            
            # Türkiye'den erişilebilir Emsal UYAP URL'leri
            search_urls = [
                f"https://emsal.uyap.gov.tr/bilgibankasi/arama?q={keyword}",
                f"https://uyap.gov.tr/emsal/arama?kelime={keyword}",
                f"https://emsal.uyap.gov.tr/",  # Ana sayfa
                f"https://uyap.gov.tr/bilgibankasi"  # Bilgi bankası
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            for url in search_urls:
                try:
                    logger.info(f"Emsal UYAP URL test edilyor: {url}")
                    response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
                        
                        # Emsal UYAP için çoklu selector stratejisi
                        selectors = [
                            'table.table tbody tr',  # Bootstrap table rows
                            'div.karar-item',  # Karar item divleri
                            'div.result-item', # Sonuç item divleri
                            'tr[onclick*="karar"]',  # Onclick eventi olan karar satırları
                            'a[href*="karar"]',  # Karar linklerini içeren a tagları
                            'div[class*="karar"]',  # Karar içeren class'lı divler
                            'li.list-group-item',  # List group items
                            'div.card-body',  # Card body divleri
                            'table tr td',  # Genel table satırları
                            'tr[class*="decision"]',  # Decision class'lı satırlar
                        ]
                        
                        flask_results = []
                        for selector in selectors:
                            elements = soup.select(selector)
                            
                            if elements and len(elements) >= 3:
                                logger.info(f"Emsal UYAP: {len(elements)} element bulundu ({selector})")
                                
                                for i, element in enumerate(elements[:page_size]):
                                    text = element.get_text(' ', strip=True)
                                    
                                    # Anlamlı içerik kontrolü
                                    if len(text) < 20:
                                        continue
                                        
                                    # UYAP Emsal spesifik bilgi çıkarma
                                    court = "UYAP Emsal"
                                    
                                    # Mahkeme/BAM bilgisi çıkarma
                                    court_patterns = [
                                        r'([a-zğüşıöçA-ZĞÜŞIÖÇ\s]+(?:bam|bölge|adliye|mahkeme)(?:si)?(?:\s*\d+\.?\s*(?:hukuk|ceza|ticaret|idari)?\s*daire(?:si)?)?)',
                                        r'(\w+\s+(?:asliye|sulh)\s+(?:hukuk|ceza)\s+mahkeme(?:si)?)',
                                        r'(\w+\s+\d+\.?\s*(?:hukuk|ceza|ticaret|idari)\s*daire(?:si)?)',
                                    ]
                                    
                                    for pattern in court_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            court = match.group(1).strip()
                                            break
                                    
                                    # Esas No çıkarma
                                    esas_patterns = [
                                        r'(?:esas|e\.?)\s*:?\s*(\d{4}/\d+)',
                                        r'(\d{4}/\d+)',  # Basit format
                                    ]
                                    esas_no = ""
                                    for pattern in esas_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            esas_no = match.group(1)
                                            break
                                    
                                    # Karar No çıkarma
                                    karar_patterns = [
                                        r'(?:karar|k\.?)\s*:?\s*(\d{4}/\d+)',
                                        r'k\.\s*(\d{4}/\d+)',
                                    ]
                                    karar_no = ""
                                    for pattern in karar_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            karar_no = match.group(1)
                                            break
                                    
                                    # Tarih çıkarma
                                    date_patterns = [
                                        r'(\d{1,2}[./]\d{1,2}[./]\d{4})',
                                        r'(\d{4}-\d{2}-\d{2})',
                                        r'(\d{1,2}\s+(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+\d{4})',
                                    ]
                                    decision_date = ""
                                    for pattern in date_patterns:
                                        match = re.search(pattern, text, re.IGNORECASE)
                                        if match:
                                            decision_date = match.group(1)
                                            break
                                    
                                    # Link bulma
                                    doc_url = ""
                                    link_elem = element.find('a', href=True)
                                    if link_elem:
                                        doc_url = link_elem['href']
                                        if not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                    elif element.get('onclick'):
                                        # onclick eventi varsa URL çıkar
                                        onclick = element.get('onclick', '')
                                        url_match = re.search(r"(?:window\.open|location\.href)\s*=?\s*['\"]([^'\"]+)['\"]", onclick)
                                        if url_match:
                                            doc_url = url_match.group(1)
                                            if not doc_url.startswith('http'):
                                                doc_url = urljoin(url, doc_url)
                                    
                                    # Sonuç oluştur
                                    result_id = f"emsal_real_{i+1}_{page_number}"
                                    title = f"{court} - {karar_no or esas_no or 'Karar'}"
                                    
                                    flask_result = YargiSearchResult(
                                        id=result_id,
                                        title=title,
                                        court=court,
                                        decision_date=decision_date,
                                        case_number=esas_no,
                                        decision_number=karar_no,
                                        summary=f"Emsal kararı: {keyword} - {text[:150]}...",
                                        document_url=doc_url or f"https://www.uyap.gov.tr/Karar/Detay/{result_id}"
                                    )
                                    flask_results.append(flask_result)
                                    
                                    if len(flask_results) >= page_size:
                                        break
                                
                                if flask_results:
                                    logger.info(f"Emsal UYAP gerçek web scraping başarılı: {len(flask_results)} sonuç")
                                    return {
                                        'decisions': flask_results,
                                        'count': len(flask_results) * 2,  # Tahmin edilen toplam
                                        'current_page': page_number,
                                        'page_size': page_size,
                                        'total_pages': 2
                                    }
                                break
                                
                    else:
                        logger.warning(f"Emsal UYAP URL başarısız: {url} - {response.status_code}")
                        
                except Exception as e:
                    logger.warning(f"Emsal UYAP URL hatası ({url}): {e}")
                    continue
            
            # Hiçbir URL çalışmadı - fallback demo
            logger.warning("Emsal UYAP: Tüm URL'ler başarısız, minimal fallback")
            
            # Son çare olarak basit demo sonuç döndür
            fallback_result = YargiSearchResult(
                id=f"emsal_fallback_{page_number}",
                title=f"UYAP Emsal Kararı - '{keyword}'",
                court="UYAP Emsal",
                decision_date="",
                case_number="",
                decision_number="",
                summary=f"'{keyword}' arama sonucu - Gerçek web sitesinden erişim sağlanamadı",
                document_url="https://emsal.uyap.gov.tr"
            )
            
            return {
                'decisions': [fallback_result],
                'count': 1,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': 1
            }

                
        except Exception as e:
            logger.error(f"Emsal web scraping hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_anayasa(self,
                             keyword: str,
                             page_number: int = 1,
                             page_size: int = 20) -> Dict[str, Any]:
        """Anayasa Mahkemesi API'sinde arama yapar - hızlı ve güvenilir"""
        
        try:
            # Önce mevcut API'yi dene - Norm Denetimi
            search_request = AnayasaNormDenetimiSearchRequest(
                keywords_all=[keyword] if keyword else [],
                keywords_any=[],
                keywords_exclude=[],
                page_to_fetch=page_number,
                results_per_page=page_size
            )
            
            logger.info(f"Anayasa Mahkemesi API arama yapılıyor: {keyword}")
            
            try:
                # API çağrısı yap
                api_response = await self.anayasa_client.search_norm_denetimi_decisions(search_request)
                
                # Sonuçları Flask formatına çevir
                flask_results = []
                if api_response.data and api_response.data.data:
                    for decision in api_response.data.data:
                        flask_result = YargiSearchResult(
                            id=decision.id,
                            title=f"Anayasa Mahkemesi - {decision.kararNo or 'Karar'}",
                            court="Anayasa Mahkemesi",
                            decision_date=decision.kararTarihi or "",
                            case_number=decision.esasNo or "",
                            decision_number=decision.kararNo or "",
                            summary=f"Anayasa Mahkemesi kararı: {keyword}"[:200],
                            document_url=f"https://normkararlarbilgibankasi.anayasa.gov.tr/Karar/Goster/{decision.id}"
                        )
                        flask_results.append(flask_result)
                
                total_records = api_response.data.recordsTotal if api_response.data else 0
                total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
                
                logger.info(f"Anayasa Mahkemesi API başarılı: {len(flask_results)} sonuç")
                
                return {
                    'decisions': flask_results,
                    'count': total_records,
                    'current_page': page_number,
                    'page_size': page_size,
                    'total_pages': total_pages
                }
                
            except Exception as api_error:
                logger.warning(f"Anayasa Mahkemesi API hatası: {api_error}")
                
                # API başarısız, bireysel başvuru API'sini dene
                try:
                    logger.info("Anayasa Mahkemesi bireysel başvuru API'si deneniyor...")
                    # Bireysel başvuru için unified modülden import
                    bireysel_request = AnayasaNormDenetimiSearchRequest(
                        keywords_all=[keyword] if keyword else [],
                        keywords_any=[],
                        keywords_exclude=[],
                        page_to_fetch=page_number,
                        results_per_page=page_size
                    )
                    
                    # Unified modüldeki client'ı kullan
                    bireysel_client = AnayasaMahkemesiApiClient()
                    api_response = await bireysel_client.search_norm_denetimi_decisions(bireysel_request)
                    
                    flask_results = []
                    if api_response.data and api_response.data.data:
                        for decision in api_response.data.data:
                            flask_result = YargiSearchResult(
                                id=decision.id,
                                title=f"Anayasa Mahkemesi (Bireysel) - {decision.kararNo or 'Karar'}",
                                court="Anayasa Mahkemesi",
                                decision_date=decision.kararTarihi or "",
                                case_number=decision.esasNo or "",
                                decision_number=decision.kararNo or "",
                                summary=f"Anayasa Mahkemesi bireysel başvuru kararı: {keyword}"[:200],
                                document_url=f"https://normkararlarbilgibankasi.anayasa.gov.tr/Karar/Goster/{decision.id}"
                            )
                            flask_results.append(flask_result)
                    
                    total_records = api_response.data.recordsTotal if api_response.data else 0
                    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
                    
                    logger.info(f"Anayasa Mahkemesi bireysel API başarılı: {len(flask_results)} sonuç")
                    
                    return {
                        'decisions': flask_results,
                        'count': total_records,
                        'current_page': page_number,
                        'page_size': page_size,
                        'total_pages': total_pages
                    }
                    
                except Exception as bireysel_error:
                    logger.warning(f"Anayasa Mahkemesi bireysel API hatası: {bireysel_error}")
                
                # Her iki API da başarısız, hızlı web scraping dene
                logger.info("Anayasa Mahkemesi hızlı web scraping deneniyor...")
                
                # Gerçek Anayasa Mahkemesi URL'leri 
                quick_urls = [
                    f"https://normkararlarbilgibankasi.anayasa.gov.tr/",  # Ana sayfa
                    f"https://www.anayasa.gov.tr/tr/kararlar/arama?q={keyword}",
                    f"https://anayasa.gov.tr/kararlar/arama?kelime={keyword}",
                    f"https://www.anayasa.gov.tr/",  # Ana sayfa
                    f"https://normkararlarbilgibankasi.anayasa.gov.tr/Ara?kelime={keyword}"
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                for url in quick_urls:
                    try:
                        logger.info(f"Anayasa Mahkemesi hızlı URL: {url}")
                        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Hızlı sonuç bulma - en yaygın selectorlar
                            quick_selectors = [
                                'tr[class*="karar"]', 'div[class*="karar"]', 
                                '.karar-item', '.result-item', 'tr td'
                            ]
                            
                            flask_results = []
                            for selector in quick_selectors:
                                elements = soup.select(selector)
                                if elements and len(elements) >= 3:  # En az 3 sonuç varsa
                                    for i, element in enumerate(elements[:page_size]):
                                        title = element.get_text(strip=True)[:100] or f"Anayasa Mahkemesi Kararı {i+1}"
                                        
                                        # Link bul
                                        link_elem = element.find('a')
                                        doc_url = link_elem.get('href', '') if link_elem else ''
                                        if doc_url and not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                        
                                        flask_result = YargiSearchResult(
                                            id=f"anayasa_{i+1}_{page_number}",
                                            title=title,
                                            court="Anayasa Mahkemesi",
                                            decision_date="",
                                            case_number="",
                                            decision_number="",
                                            summary=f"Anayasa Mahkemesi kararı: {keyword}",
                                            document_url=doc_url or f"https://normkararlarbilgibankasi.anayasa.gov.tr/Karar/Goster/anayasa_{i+1}_{page_number}"
                                        )
                                        flask_results.append(flask_result)
                                    
                                    if flask_results:
                                        logger.info(f"Anayasa Mahkemesi hızlı scraping başarılı: {len(flask_results)} sonuç")
                                        return {
                                            'decisions': flask_results,
                                            'count': len(flask_results),
                                            'current_page': page_number,
                                            'page_size': page_size,
                                            'total_pages': 1
                                        }
                                    break
                            
                    except Exception as url_error:
                        logger.warning(f"Anayasa Mahkemesi hızlı URL hatası: {url_error}")
                        continue
                
                # Hiçbir yöntem çalışmadı
                logger.warning("Anayasa Mahkemesi: Tüm yöntemler başarısız")
                return self._empty_response(page_number, page_size)
            
        except Exception as e:
            logger.error(f"Anayasa Mahkemesi arama hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_uyusmazlik(self,
                                keyword: str,
                                page_number: int = 1,
                                page_size: int = 20) -> Dict[str, Any]:
        """Uyuşmazlık Mahkemesi API'sinde arama yapar - hızlı ve güvenilir"""
        
        try:
            # Uyuşmazlık Mahkemesi arama parametrelerini hazırla
            search_request = UyusmazlikSearchRequest(
                icerik=keyword,
                bolum=None,  # Tüm bölümlerde ara
                uyusmazlik_turu=None,
                karar_sonuclari=[],
                esas_yil="",
                esas_sayisi="",
                karar_yil="",
                karar_sayisi="",
                kanun_no="",
                karar_date_begin="",
                karar_date_end="",
                resmi_gazete_sayi="",
                resmi_gazete_date="",
                tumce="",
                wild_card="",
                hepsi="",
                herhangi_birisi="",
                not_hepsi=""
            )
            
            logger.info(f"Uyuşmazlık Mahkemesi API arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.uyusmazlik_client.search_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.decisions:
                for decision in api_response.decisions[:page_size]:  # Sayfalama için sınırla
                    # Model alanlarını doğru şekilde kullan
                    karar_sayisi = getattr(decision, 'karar_sayisi', None) or getattr(decision, 'kararSayisi', None) or f'UM_{page_number}_{len(flask_results)+1}'
                    esas_sayisi = getattr(decision, 'esas_sayisi', None) or getattr(decision, 'esasSayisi', None) or 'N/A'
                    karar_tarihi = getattr(decision, 'karar_tarihi', None) or getattr(decision, 'kararTarihi', None) or ""
                    
                    flask_result = YargiSearchResult(
                        id=str(karar_sayisi),
                        title=f"Uyuşmazlık Mahkemesi - {karar_sayisi}",
                        court="Uyuşmazlık Mahkemesi",
                        decision_date=karar_tarihi,
                        case_number=esas_sayisi,
                        decision_number=str(karar_sayisi),
                        summary=f"Uyuşmazlık Mahkemesi kararı: {keyword}"[:200],
                        document_url=f"https://kararlar.uyusmazlik.gov.tr/Karar/Detay/{karar_sayisi}"
                    )
                    flask_results.append(flask_result)
            
            total_records = getattr(api_response, 'total_records_found', len(flask_results)) or len(flask_results)
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"Uyuşmazlık Mahkemesi API başarılı: {len(flask_results)} sonuç")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Uyuşmazlık Mahkemesi arama hatası: {e}")
            
            # API başarısız, hızlı web scraping dene
            try:
                logger.info("Uyuşmazlık Mahkemesi hızlı web scraping deneniyor...")
                
                quick_urls = [
                    f"https://kararlar.uyusmazlik.gov.tr/arama?q={keyword}",
                    f"https://www.uyusmazlik.gov.tr/kararlar/arama?kelime={keyword}"
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Connection': 'keep-alive',
                }
                
                for url in quick_urls:
                    try:
                        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Hızlı sonuç bulma
                            quick_selectors = [
                                'tr[class*="karar"]', 'div[class*="karar"]',
                                '.karar-item', '.result-item', 'tr td',
                                'div[class*="decision"]', 'li[class*="result"]'
                            ]
                            
                            flask_results = []
                            for selector in quick_selectors:
                                elements = soup.select(selector)
                                if elements and len(elements) >= 3:
                                    for i, element in enumerate(elements[:page_size]):
                                        title = element.get_text(strip=True)[:100] or f"Uyuşmazlık Mahkemesi Kararı {i+1}"
                                        
                                        link_elem = element.find('a')
                                        doc_url = link_elem.get('href', '') if link_elem else ''
                                        if doc_url and not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                        
                                        result_id = f"uyusmazlik_{i+1}_{page_number}"
                                        flask_result = YargiSearchResult(
                                            id=result_id,
                                            title=title,
                                            court="Uyuşmazlık Mahkemesi",
                                            decision_date="",
                                            case_number="",
                                            decision_number="",
                                            summary=f"Uyuşmazlık Mahkemesi kararı: {keyword}",
                                            document_url=doc_url or f"https://kararlar.uyusmazlik.gov.tr/Karar/Detay/{result_id}"
                                        )
                                        flask_results.append(flask_result)
                                    
                                    if flask_results:
                                        logger.info(f"Uyuşmazlık Mahkemesi hızlı scraping başarılı: {len(flask_results)} sonuç")
                                        return {
                                            'decisions': flask_results,
                                            'count': len(flask_results),
                                            'current_page': page_number,
                                            'page_size': page_size,
                                            'total_pages': 1
                                        }
                                    break
                                    
                    except Exception as url_error:
                        logger.warning(f"Uyuşmazlık Mahkemesi hızlı URL hatası: {url_error}")
                        continue
                        
            except Exception as scraping_error:
                logger.warning(f"Uyuşmazlık Mahkemesi web scraping hatası: {scraping_error}")
            
            return self._empty_response(page_number, page_size)
    
    async def _search_kik(self,
                         keyword: str,
                         page_number: int = 1,
                         page_size: int = 20) -> Dict[str, Any]:
        """KİK API'sinde arama yapar - hızlı ve güvenilir"""
        
        try:
            # KİK arama parametrelerini hazırla
            search_request = KikSearchRequest(
                karar_tipi=KikKararTipi.UYUSMAZLIK,  # Default olarak UYUSMAZLIK kullan
                karar_no=None,
                karar_tarihi_baslangic=None,
                karar_tarihi_bitis=None,
                resmi_gazete_sayisi=None,
                resmi_gazete_tarihi=None,
                basvuru_konusu_ihale=None,
                basvuru_sahibi=None,
                ihaleyi_yapan_idare=None,
                yil=None,
                karar_metni=keyword,
                page=page_number
            )
            
            logger.info(f"KİK API arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.kik_client.search_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.decisions:
                for decision in api_response.decisions[:page_size]:  # Sayfalama için sınırla
                    # Model alanlarını doğru şekilde kullan
                    karar_no = getattr(decision, 'karar_no_str', None) or getattr(decision, 'kararNo', None) or f'KIK_{page_number}_{len(flask_results)+1}'
                    karar_tarihi = getattr(decision, 'karar_tarihi_str', None) or getattr(decision, 'kararTarihi', '') or ""
                    
                    flask_result = YargiSearchResult(
                        id=str(karar_no),
                        title=f"KİK - {karar_no}",
                        court="Kamu İhale Kurumu",
                        decision_date=karar_tarihi,
                        case_number="N/A",
                        decision_number=str(karar_no),
                        summary=f"KİK kararı: {keyword}"[:200],
                        document_url=f"https://www.kik.gov.tr/Kararlar/Detay/{karar_no}"
                    )
                    flask_results.append(flask_result)
            
            total_records = getattr(api_response, 'total_records', len(flask_results))
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"KİK API başarılı: {len(flask_results)} sonuç")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"KİK arama hatası: {e}")
            
            # API başarısız, hızlı web scraping dene
            try:
                logger.info("KİK hızlı web scraping deneniyor...")
                
                quick_urls = [
                    f"https://www.kik.gov.tr/Kararlar/Arama?kelime={keyword}",
                    f"https://kik.gov.tr/kararlar/arama?q={keyword}"
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Connection': 'keep-alive',
                }
                
                for url in quick_urls:
                    try:
                        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Hızlı sonuç bulma
                            quick_selectors = [
                                'tr[class*="karar"]', 'div[class*="karar"]',
                                '.karar-item', '.result-item', 'tr td',
                                'div[class*="decision"]', 'li[class*="result"]',
                                'table tr', 'tbody tr'
                            ]
                            
                            flask_results = []
                            for selector in quick_selectors:
                                elements = soup.select(selector)
                                if elements and len(elements) >= 3:
                                    for i, element in enumerate(elements[:page_size]):
                                        title = element.get_text(strip=True)[:100] or f"KİK Kararı {i+1}"
                                        
                                        link_elem = element.find('a')
                                        doc_url = link_elem.get('href', '') if link_elem else ''
                                        if doc_url and not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                        
                                        result_id = f"kik_{i+1}_{page_number}"
                                        flask_result = YargiSearchResult(
                                            id=result_id,
                                            title=title,
                                            court="Kamu İhale Kurumu",
                                            decision_date="",
                                            case_number="",
                                            decision_number="",
                                            summary=f"KİK kararı: {keyword}",
                                            document_url=doc_url or f"https://www.kik.gov.tr/Kararlar/Detay/{result_id}"
                                        )
                                        flask_results.append(flask_result)
                                    
                                    if flask_results:
                                        logger.info(f"KİK hızlı scraping başarılı: {len(flask_results)} sonuç")
                                        return {
                                            'decisions': flask_results,
                                            'count': len(flask_results),
                                            'current_page': page_number,
                                            'page_size': page_size,
                                            'total_pages': 1
                                        }
                                    break
                                    
                    except Exception as url_error:
                        logger.warning(f"KİK hızlı URL hatası: {url_error}")
                        continue
                        
            except Exception as scraping_error:
                logger.warning(f"KİK web scraping hatası: {scraping_error}")
            
            return self._empty_response(page_number, page_size)
    
    async def _search_rekabet(self,
                             keyword: str,
                             page_number: int = 1,
                             page_size: int = 20) -> Dict[str, Any]:
        """Rekabet Kurumu API'sinde arama yapar - hızlı ve güvenilir"""
        
        try:
            # Rekabet Kurumu arama parametrelerini hazırla
            search_request = RekabetKurumuSearchRequest(
                sayfaAdi=None,
                YayinlanmaTarihi=None,
                PdfText=keyword,
                KararTuruID=None,
                KararSayisi=None,
                KararTarihi=None,
                page=page_number
            )
            
            logger.info(f"Rekabet Kurumu API arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.rekabet_client.search_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.decisions:
                for decision in api_response.decisions[:page_size]:  # Sayfalama için sınırla
                    karar_id = getattr(decision, 'karar_id', None) or f'RK_{page_number}_{len(flask_results)+1}'
                    decision_number = getattr(decision, 'decision_number', None) or getattr(decision, 'kararSayisi', '') or ""
                    decision_date = getattr(decision, 'decision_date', None) or getattr(decision, 'kararTarihi', '') or ""
                    decision_url = getattr(decision, 'decision_url', None) or ""
                    
                    flask_result = YargiSearchResult(
                        id=str(karar_id),
                        title=f"Rekabet Kurumu - {decision_number or karar_id}",
                        court="Rekabet Kurumu",
                        decision_date=decision_date,
                        case_number="N/A",
                        decision_number=decision_number,
                        summary=f"Rekabet Kurumu kararı: {keyword}"[:200],
                        document_url=str(decision_url) if decision_url else f"https://www.rekabet.gov.tr/Karar/Detay/{karar_id}"
                    )
                    flask_results.append(flask_result)
            
            # total_records özelliğini güvenli şekilde al
            total_records = getattr(api_response, 'total_records', len(flask_results))
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"Rekabet Kurumu API başarılı: {len(flask_results)} sonuç")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Rekabet Kurumu arama hatası: {e}")
            
            # API başarısız, hızlı web scraping dene
            try:
                logger.info("Rekabet Kurumu hızlı web scraping deneniyor...")
                
                quick_urls = [
                    f"https://www.rekabet.gov.tr/Karar/Arama?kelime={keyword}",
                    f"https://rekabet.gov.tr/kararlar/arama?q={keyword}"
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Connection': 'keep-alive',
                }
                
                for url in quick_urls:
                    try:
                        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Hızlı sonuç bulma
                            quick_selectors = [
                                'tr[class*="karar"]', 'div[class*="karar"]',
                                '.karar-item', '.result-item', 'tr td',
                                'div[class*="decision"]', 'li[class*="result"]',
                                'table tr', 'tbody tr'
                            ]
                            
                            flask_results = []
                            for selector in quick_selectors:
                                elements = soup.select(selector)
                                if elements and len(elements) >= 3:
                                    for i, element in enumerate(elements[:page_size]):
                                        title = element.get_text(strip=True)[:100] or f"Rekabet Kurumu Kararı {i+1}"
                                        
                                        link_elem = element.find('a')
                                        doc_url = link_elem.get('href', '') if link_elem else ''
                                        if doc_url and not doc_url.startswith('http'):
                                            doc_url = urljoin(url, doc_url)
                                        
                                        result_id = f"rekabet_{i+1}_{page_number}"
                                        flask_result = YargiSearchResult(
                                            id=result_id,
                                            title=title,
                                            court="Rekabet Kurumu",
                                            decision_date="",
                                            case_number="",
                                            decision_number="",
                                            summary=f"Rekabet Kurumu kararı: {keyword}",
                                            document_url=doc_url or f"https://www.rekabet.gov.tr/Karar/Detay/{result_id}"
                                        )
                                        flask_results.append(flask_result)
                                    
                                    if flask_results:
                                        logger.info(f"Rekabet Kurumu hızlı scraping başarılı: {len(flask_results)} sonuç")
                                        return {
                                            'decisions': flask_results,
                                            'count': len(flask_results),
                                            'current_page': page_number,
                                            'page_size': page_size,
                                            'total_pages': 1
                                        }
                                    break
                                    
                    except Exception as url_error:
                        logger.warning(f"Rekabet Kurumu hızlı URL hatası: {url_error}")
                        continue
                        
            except Exception as scraping_error:
                logger.warning(f"Rekabet Kurumu web scraping hatası: {scraping_error}")
            
            return self._empty_response(page_number, page_size)
    
    def get_court_options(self) -> Dict[str, List[Dict[str, str]]]:
        """Mahkeme seçeneklerini döndürür"""
        return {
            "yargitay": [
                # Hukuk Daireleri
                {'value': '1. Hukuk Dairesi', 'text': '1. Hukuk Dairesi'},
                {'value': '2. Hukuk Dairesi', 'text': '2. Hukuk Dairesi'},
                {'value': '3. Hukuk Dairesi', 'text': '3. Hukuk Dairesi'},
                {'value': '4. Hukuk Dairesi', 'text': '4. Hukuk Dairesi'},
                {'value': '5. Hukuk Dairesi', 'text': '5. Hukuk Dairesi'},
                {'value': '6. Hukuk Dairesi', 'text': '6. Hukuk Dairesi'},
                {'value': '7. Hukuk Dairesi', 'text': '7. Hukuk Dairesi'},
                {'value': '8. Hukuk Dairesi', 'text': '8. Hukuk Dairesi'},
                {'value': '9. Hukuk Dairesi', 'text': '9. Hukuk Dairesi'},
                {'value': '10. Hukuk Dairesi', 'text': '10. Hukuk Dairesi'},
                {'value': '11. Hukuk Dairesi', 'text': '11. Hukuk Dairesi'},
                {'value': '12. Hukuk Dairesi', 'text': '12. Hukuk Dairesi'},
                {'value': '13. Hukuk Dairesi', 'text': '13. Hukuk Dairesi'},
                {'value': '14. Hukuk Dairesi', 'text': '14. Hukuk Dairesi'},
                {'value': '15. Hukuk Dairesi', 'text': '15. Hukuk Dairesi'},
                {'value': '16. Hukuk Dairesi', 'text': '16. Hukuk Dairesi'},
                {'value': '17. Hukuk Dairesi', 'text': '17. Hukuk Dairesi'},
                {'value': '18. Hukuk Dairesi', 'text': '18. Hukuk Dairesi'},
                {'value': '19. Hukuk Dairesi', 'text': '19. Hukuk Dairesi'},
                {'value': '20. Hukuk Dairesi', 'text': '20. Hukuk Dairesi'},
                {'value': '21. Hukuk Dairesi', 'text': '21. Hukuk Dairesi'},
                {'value': '22. Hukuk Dairesi', 'text': '22. Hukuk Dairesi'},
                {'value': '23. Hukuk Dairesi', 'text': '23. Hukuk Dairesi'},
                # Ceza Daireleri
                {'value': '1. Ceza Dairesi', 'text': '1. Ceza Dairesi'},
                {'value': '2. Ceza Dairesi', 'text': '2. Ceza Dairesi'},
                {'value': '3. Ceza Dairesi', 'text': '3. Ceza Dairesi'},
                {'value': '4. Ceza Dairesi', 'text': '4. Ceza Dairesi'},
                {'value': '5. Ceza Dairesi', 'text': '5. Ceza Dairesi'},
                {'value': '6. Ceza Dairesi', 'text': '6. Ceza Dairesi'},
                {'value': '7. Ceza Dairesi', 'text': '7. Ceza Dairesi'},
                {'value': '8. Ceza Dairesi', 'text': '8. Ceza Dairesi'},
                {'value': '9. Ceza Dairesi', 'text': '9. Ceza Dairesi'},
                {'value': '10. Ceza Dairesi', 'text': '10. Ceza Dairesi'},
                {'value': '11. Ceza Dairesi', 'text': '11. Ceza Dairesi'},
                {'value': '12. Ceza Dairesi', 'text': '12. Ceza Dairesi'},
                {'value': '13. Ceza Dairesi', 'text': '13. Ceza Dairesi'},
                {'value': '14. Ceza Dairesi', 'text': '14. Ceza Dairesi'},
                {'value': '15. Ceza Dairesi', 'text': '15. Ceza Dairesi'},
                {'value': '16. Ceza Dairesi', 'text': '16. Ceza Dairesi'},
                # Kurullar
                {'value': 'Hukuk Genel Kurulu', 'text': 'Hukuk Genel Kurulu'},
                {'value': 'Ceza Genel Kurulu', 'text': 'Ceza Genel Kurulu'},
                {'value': 'İçtihadı Birleştirme Kurulu', 'text': 'İçtihadı Birleştirme Kurulu'}
            ],
            "danistay": [
                # İdari Dava Daireleri
                {'value': '1. Daire', 'text': '1. Daire'},
                {'value': '2. Daire', 'text': '2. Daire'},
                {'value': '3. Daire', 'text': '3. Daire'},
                {'value': '4. Daire', 'text': '4. Daire'},
                {'value': '5. Daire', 'text': '5. Daire'},
                {'value': '6. Daire', 'text': '6. Daire'},
                {'value': '8. Daire', 'text': '8. Daire'},
                {'value': '10. Daire', 'text': '10. Daire'},
                {'value': '12. Daire', 'text': '12. Daire'},
                {'value': '13. Daire', 'text': '13. Daire'},
                {'value': '14. Daire', 'text': '14. Daire'},
                {'value': '15. Daire', 'text': '15. Daire'},
                # Vergi Dava Daireleri
                {'value': '7. Daire', 'text': '7. Daire (Vergi)'},
                {'value': '9. Daire', 'text': '9. Daire (Vergi)'},
                {'value': '11. Daire', 'text': '11. Daire (Vergi)'},
                # Kurullar
                {'value': 'İdari Dava Daireleri Kurulu', 'text': 'İdari Dava Daireleri Kurulu'},
                {'value': 'Vergi Dava Daireleri Kurulu', 'text': 'Vergi Dava Daireleri Kurulu'}
            ],
            "emsal": [
                {'value': 'Tüm Mahkemeler', 'text': 'Tüm Mahkemeler'}
            ],
            "anayasa": [
                {'value': 'Norm Denetimi', 'text': 'Norm Denetimi'},
                {'value': 'Bireysel Başvuru', 'text': 'Bireysel Başvuru'}
            ],
            "uyusmazlik": [
                {'value': 'Hukuk Bölümü', 'text': 'Hukuk Bölümü'},
                {'value': 'Ceza Bölümü', 'text': 'Ceza Bölümü'},
                {'value': 'Genel Kurul', 'text': 'Genel Kurul'}
            ],
            "kik": [
                {'value': 'Kurul Kararları', 'text': 'Kurul Kararları'},
                {'value': 'İtiraz Değerlendirme', 'text': 'İtiraz Değerlendirme'}
            ],
            "rekabet": [
                {'value': 'Kurul Kararları', 'text': 'Kurul Kararları'}
            ]
        }

    # Doküman içeriği alma metodları
    async def _get_yargitay_document_content(self, document_id: str) -> Dict[str, Any]:
        """Yargıtay kararının tam içeriğini çoklu yöntemle getirir - süper gelişmiş versiyon."""
        
        # Farklı URL formatlarını dene
        url_formats = [
            f"https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/pf/bilgi-bankasi-detay.xhtml?id={document_id}",
            f"https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/pf/detay.xhtml?id={document_id}",
            f"https://karararama.yargitay.gov.tr/detay/{document_id}",
            f"https://www.yargitay.gov.tr/kategori/4/{document_id}",
            f"https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/pf/karardetay.xhtml?id={document_id}",
            f"https://karararama.yargitay.gov.tr/api/karar/{document_id}",  # API endpoint deneme
            f"https://karararama.yargitay.gov.tr/pdf/{document_id}.pdf"  # Direkt PDF deneme
        ]
        
        # Farklı scraping yöntemleri
        scraping_methods = [
            ('normal', self.http_manager.get_content),
            ('different_agents', self.http_manager.get_content_with_different_agents),
            ('session_retry', self.http_manager.get_content_with_session_retry)
        ]
        
        for url_idx, source_url in enumerate(url_formats):
            for method_idx, (method_name, method_func) in enumerate(scraping_methods):
                attempt = (url_idx * len(scraping_methods)) + method_idx + 1
                total_attempts = len(url_formats) * len(scraping_methods)
                
                try:
                    logger.info(f"Yargıtay karar metni deneme {attempt}/{total_attempts}: {source_url} ({method_name})")
                    
                    # HTTP isteği ile sayfayı çek
                    response = method_func(source_url, timeout=25)
                    if not response:
                        logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                        continue
                    
                    # PDF kontrolü
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        logger.info(f"Deneme {attempt}: PDF bulundu")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'yargitay',
                            'extraction_method': f"PDF - {method_name}"
                        }
                    
                    # JSON API response kontrolü
                    if 'json' in content_type:
                        try:
                            json_data = response.json()
                            if 'content' in json_data or 'text' in json_data or 'karar' in json_data:
                                content = json_data.get('content') or json_data.get('text') or json_data.get('karar', '')
                                if len(content) > 200:
                                    logger.info(f"Deneme {attempt}: JSON API'den içerik alındı")
                                    return {
                                        'success': True, 
                                        'content': content, 
                                        'content_type': 'text', 
                                        'source_url': source_url, 
                                        'court_type': 'yargitay',
                                        'extraction_method': f"JSON API - {method_name}"
                                    }
                        except:
                            pass
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Gereksiz elementleri kaldır
                    for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select", "noscript"]):
                        element.decompose()
                    
                    # Çoklu selector deneme - genişletilmiş
                    selectors_groups = [
                        # Yargıtay spesifik selectorlar
                        ["div.ui-panel-content", "div.ui-widget-content", "div.karar-metni", "div.karar-icerik"],
                        # Genel content selectorlar
                        ["div[id*='panel']", "div[class*='content']", "div[class*='karar']", "div[class*='detay']"],
                        # Tablo ve liste selectorlar
                        ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                        # Primefaces selectorlar (Yargıtay genelde Primefaces kullanır)
                        ["div[id*='form']", "div[class*='ui-']", "span[class*='ui-']", "p[class*='ui-']"],
                        # Iframe içeriği
                        ["iframe", "embed", "object"],
                        # Fallback selectorlar
                        ["main", "article", "section", ".container", ".content"]
                    ]
                    
                    best_text = ""
                    best_source = ""
                    
                    for group_idx, selectors in enumerate(selectors_groups):
                        for selector in selectors:
                            elements = soup.select(selector)
                            for element in elements:
                                # Iframe içeriği için özel işlem
                                if element.name in ['iframe', 'embed', 'object']:
                                    src = element.get('src')
                                    if src:
                                        try:
                                            iframe_response = self.http_manager.get_content(urljoin(source_url, src))
                                            if iframe_response:
                                                iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                                                text = iframe_soup.get_text(separator='\n', strip=True)
                                            else:
                                                continue
                                        except:
                                            continue
                                    else:
                                        continue
                                else:
                                    text = element.get_text(separator='\n', strip=True)
                                
                                # Karar metni olabilecek içeriği filtrele - daha esnek kriterler
                                if (len(text) > len(best_text) and 
                                    len(text) > 150 and  # Daha düşük minimum
                                    (any(keyword in text.lower() for keyword in ['karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'esas', 'sonuç', 'davacı', 'davalı', 'başvuran', 'müdahil', 'temyiz', 'istinaf', 'dosya', 'duruşma', 'delil', 'tanık', 'bilirkişi', 'keşif', 'hukuki', 'kanun', 'madde', 'fıkra', 'bent', 'yönetmelik', 'tebliğ', 'icra', 'infaz', 'takip', 'haciz', 'satış']) or
                                     len(text) > 1000)):  # Ya da çok uzun ise
                                    best_text = text
                                    best_source = f"Group {group_idx+1}, Selector: {selector}"
                                    logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                    
                    # Eğer spesifik selector bulamazsa, body'den al - geliştirilmiş
                    if len(best_text) < 400 and soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        # Daha akıllı filtreleme
                        lines = body_text.split('\n')
                        filtered_lines = []
                        skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış']
                        
                        for line in lines:
                            line = line.strip()
                            if (len(line) > 10 and  # Daha düşük minimum
                                not any(skip in line.lower() for skip in skip_keywords) and
                                not line.startswith('http') and
                                not line.isdigit() and
                                not re.match(r'^[\s\.\-\,]+$', line)):  # Sadece noktalama işareti olan satırları atla
                                filtered_lines.append(line)
                        
                        if len(filtered_lines) > 5:  # En az 5 satır varsa
                            best_text = '\n'.join(filtered_lines)
                            best_source = "Body fallback enhanced"
                            logger.info(f"Deneme {attempt}: Body'den metin alındı - {len(best_text)} karakter")
                    
                    # Metni temizle - daha az agresif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:  # Daha düşük minimum
                        logger.info(f"Yargıtay metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'yargitay',
                            'extraction_method': f"Attempt {attempt} - {best_source} ({method_name})"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                        
                except Exception as e:
                    logger.error(f"Deneme {attempt} hatası: {e}")
                    continue
        
        # Tüm denemeler başarısız oldu - son çare olarak orijinal URL ile yönlendirme
        original_url = url_formats[0]
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'redirect_url': original_url, 
            'source_url': original_url, 
            'court_type': 'yargitay',
            'error_info': 'Tüm extraction yöntemleri başarısız oldu'
        }

    async def _get_danistay_document_content(self, document_id: str) -> Dict[str, Any]:
        """Danıştay kararının tam içeriğini çoklu yöntemle getirir."""
        
        # Farklı URL formatlarını dene
        url_formats = [
            f"https://karararama.danistay.gov.tr/getDokuman?id={document_id}",
            f"https://karararama.danistay.gov.tr/dokuman/{document_id}",
            f"https://www.danistay.gov.tr/Kararlar/DetayGoster/{document_id}",
            f"https://karararama.danistay.gov.tr/detay?id={document_id}",
            f"https://karararama.danistay.gov.tr/karar/{document_id}"
        ]
        
        for attempt, source_url in enumerate(url_formats, 1):
            try:
                logger.info(f"Danıştay karar metni deneme {attempt}/{len(url_formats)}: {source_url}")
                
                # Önce HEAD isteği ile içerik tipini kontrol et
                try:
                    head_response = requests.head(source_url, timeout=10, allow_redirects=True)
                    if 'pdf' in head_response.headers.get('content-type', '').lower():
                        logger.info(f"Deneme {attempt}: PDF bulundu (HEAD)")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'danistay'
                        }
                except:
                    pass  # HEAD isteği başarısız olursa GET ile devam et
                
                # GET isteği ile sayfayı çek
                response = self.http_manager.get_content(source_url, timeout=20)
                if not response:
                    logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                    continue
                
                # PDF kontrolü
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' in content_type:
                    logger.info(f"Deneme {attempt}: PDF tespit edildi")
                    return {
                        'success': True, 
                        'content_type': 'pdf', 
                        'pdf_url': source_url, 
                        'source_url': source_url, 
                        'court_type': 'danistay'
                    }
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Gereksiz elementleri kaldır
                for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select"]):
                    element.decompose()
                
                # Çoklu selector deneme - Danıştay genelde <pre> tag'i kullanır
                selectors_groups = [
                    # Danıştay spesifik selectorlar
                    ["pre", "div.karar-metni", "div.karar-icerik", "div.dokuman-icerik"],
                    # Genel content selectorlar
                    ["div[class*='content']", "div[class*='karar']", "div[class*='detay']", "div[class*='dokuman']"],
                    # Tablo ve liste selectorlar
                    ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                    # Fallback selectorlar
                    ["main", "article", "section", ".container", ".content", "body"]
                ]
                
                best_text = ""
                best_source = ""
                
                for group_idx, selectors in enumerate(selectors_groups):
                    for selector in selectors:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text(separator='\n', strip=True)
                            # Danıştay için özel kriterler
                            if (len(text) > len(best_text) and 
                                len(text) > 200 and
                                any(keyword in text.lower() for keyword in ['danıştay', 'karar', 'hüküm', 'gerekçe', 'dava', 'esas', 'sonuç', 'başvuru'])):
                                best_text = text
                                best_source = f"Group {group_idx+1}, Selector: {selector}"
                                logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                                if selector == "pre":  # pre tag'i bulunduysa, bu en iyi seçenek
                                    break
                    if best_source.endswith("pre"):  # pre tag bulunduysa diğer grupları deneme
                        break
                
                # Eğer spesifik selector bulamazsa, body'den al
                if len(best_text) < 500 and soup.body:
                    body_text = soup.body.get_text(separator='\n', strip=True)
                    # Sadece karar metni gibi görünen kısımları al
                    lines = body_text.split('\n')
                    filtered_lines = []
                    skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış', 'danıştay.gov.tr']
                    
                    for line in lines:
                        line = line.strip()
                        if (len(line) > 15 and 
                            not any(skip in line.lower() for skip in skip_keywords) and
                            not line.startswith('http') and
                            not line.isdigit()):
                            filtered_lines.append(line)
                    
                    if len(filtered_lines) > 10:  # En az 10 satır varsa
                        best_text = '\n'.join(filtered_lines)
                        best_source = "Body fallback"
                        logger.info(f"Deneme {attempt}: Body'den metin alındı - {len(best_text)} karakter")
                
                                    # Metni temizle - hafif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Eğer temizleme sonrası metin çok kısaldıysa, orijinal metni kullan
                    if len(cleaned_text) < 100 and len(best_text) > 1000:
                        logger.warning(f"Danıştay: Temizleme çok agresif oldu ({len(cleaned_text)} < 100 ama orijinal {len(best_text)}), orijinal metin kullanılıyor")
                        cleaned_text = best_text[:5000]  # İlk 5000 karakteri al
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:  # Daha düşük minimum
                        logger.info(f"Danıştay metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'danistay',
                            'extraction_method': f"Attempt {attempt} - {best_source}"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                    
            except Exception as e:
                logger.error(f"Deneme {attempt} hatası: {e}")
                continue
        
        # Tüm denemeler başarısız oldu - son çare olarak orijinal URL ile yönlendirme
        original_url = url_formats[0]
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'redirect_url': original_url, 
            'source_url': original_url, 
            'court_type': 'danistay',
            'error_info': 'Tüm extraction yöntemleri başarısız oldu'
        }

    async def _get_emsal_document_content(self, document_id: str) -> Dict[str, Any]:
        """UYAP Emsal kararının tam içeriğini çoklu yöntemle getirir - Yargıtay benzeri gelişmiş sistem."""
        
        # Farklı URL formatlarını dene - UYAP spesifik (MCP Client URL'si öncelikli)
        url_formats = [
            f"https://emsal.uyap.gov.tr/getDokuman?id={document_id}",  # MCP Client'ın kullandığı URL
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/getDokuman?id={document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/bilgi-bankasi-detay.xhtml?id={document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/detay.xhtml?id={document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/karardetay.xhtml?id={document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/karar-detay.xhtml?kararId={document_id}",
            f"https://emsal.uyap.gov.tr/detay/{document_id}",
            f"https://www.uyap.gov.tr/emsal/detay/{document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/karardetay.jsp?id={document_id}",
            f"https://emsal.uyap.gov.tr/api/karar/{document_id}"
        ]
        
        # Farklı scraping yöntemleri
        scraping_methods = [
            ('normal', self.http_manager.get_content),
            ('different_agents', self.http_manager.get_content_with_different_agents),
            ('session_retry', self.http_manager.get_content_with_session_retry)
        ]
        
        for url_idx, source_url in enumerate(url_formats):
            for method_idx, (method_name, method_func) in enumerate(scraping_methods):
                attempt = (url_idx * len(scraping_methods)) + method_idx + 1
                total_attempts = len(url_formats) * len(scraping_methods)
                
                try:
                    logger.info(f"Emsal karar metni deneme {attempt}/{total_attempts}: {source_url} ({method_name})")
                    
                    # HTTP isteği ile sayfayı çek
                    response = method_func(source_url, timeout=25)
                    if not response:
                        logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                        continue
                    
                    # PDF kontrolü
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        logger.info(f"Deneme {attempt}: PDF bulundu")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'emsal',
                            'extraction_method': f"PDF - {method_name}"
                        }
                    
                    # JSON API kontrolü
                    if 'json' in content_type or '/api/' in source_url:
                        try:
                            json_data = response.json()
                            if isinstance(json_data, dict) and 'content' in json_data:
                                logger.info(f"Deneme {attempt}: JSON API'den metin alındı")
                                return {
                                    'success': True, 
                                    'content': json_data['content'], 
                                    'content_type': 'text', 
                                    'source_url': source_url, 
                                    'court_type': 'emsal',
                                    'extraction_method': f"JSON API - {method_name}"
                                }
                        except:
                            pass
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Gereksiz elementleri kaldır
                    for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select", "noscript"]):
                        element.decompose()
                    
                    best_text = ""
                    best_source = ""
                    
                    # UYAP Emsal özel parsing - getDokuman URL'si için
                    if '/getDokuman?' in source_url:
                        # Bu URL'ler doğrudan HTML karar metni döndürür
                        # UYAP özel HTML yapısını handle et
                        
                        # Önce script ve style taglerini temizle
                        for script_style in soup(["script", "style", "meta", "link"]):
                            script_style.decompose()
                        
                        # UYAP getDokuman sayfasından metin çıkartma stratejileri
                        parsing_strategies = []
                        
                        # Strateji 1: Doğrudan body içeriği
                        if soup.body:
                            body_text = soup.body.get_text(separator='\n', strip=True)
                            if len(body_text) > 200:
                                parsing_strategies.append(("Direct body text", body_text))
                        
                        # Strateji 2: Tüm text content
                        full_text = soup.get_text(separator='\n', strip=True)
                        if len(full_text) > 200:
                            parsing_strategies.append(("Full page text", full_text))
                        
                        # Strateji 3: HTML içeriğini satır satır işle
                        html_content = str(soup)
                        if len(html_content) > 500:
                            # HTML'den metin çıkar ve temizle
                            import re
                            # HTML taglerini kaldır
                            text_content = re.sub(r'<[^>]+>', ' ', html_content)
                            # HTML entity'leri decode et
                            text_content = html.unescape(text_content)
                            # Çoklu boşlukları temizle
                            text_content = re.sub(r'\s+', ' ', text_content)
                            # Satırlara böl
                            text_content = re.sub(r'\s*\n\s*', '\n', text_content)
                            
                            if len(text_content) > 200:
                                parsing_strategies.append(("HTML regex parsing", text_content))
                        
                        # En iyi stratejiyi seç
                        for strategy_name, content in parsing_strategies:
                            lines = content.split('\n')
                            karar_lines = []
                            
                            # UYAP içerik filtreleme - daha esnek
                            collecting = False
                            for line in lines:
                                line = line.strip()
                                if not line or len(line) < 5:
                                    continue
                                
                                # Karar başlangıcı anahtar kelimeleri - genişletilmiş
                                start_keywords = [
                                    'karar', 'hüküm', 'gerekçe', 'türkiye', 'cumhuriyet',
                                    'mahkeme', 'dava', 'esas', 'davacı', 'davalı', 'taraf',
                                    'başvuran', 'müdahil', 'kanun', 'madde', 'fıkra',
                                    'antalya', 'istanbul', 'ankara', 'izmir', 'bursa',
                                    'adliye', 'sulh', 'asliye', 'ticaret', 'aile',
                                    'tarih', 'sayı', 'dosya', 'esas no', 'karar no'
                                ]
                                
                                # Skip gereksiz satırlar
                                skip_patterns = [
                                    r'^(javascript|function|var\s|document\.|window\.)',
                                    r'^(http|www\.|ftp)',
                                    r'^[\d\s\-\.\/\:\;]+$',  # Sadece sayı ve noktalama
                                    r'^[^\w\sçğıöşüÇĞIİÖŞÜ]+$',  # Sadece özel karakter
                                    r'(cookie|çerez|primetime|primefaces)',
                                    r'^(null|undefined|NaN)$'
                                ]
                                
                                should_skip = False
                                for pattern in skip_patterns:
                                    if re.search(pattern, line, re.IGNORECASE):
                                        should_skip = True
                                        break
                                
                                if should_skip:
                                    continue
                                
                                # Karar metni başladıysa topla
                                if any(keyword in line.lower() for keyword in start_keywords):
                                    collecting = True
                                
                                # İçerik toplama
                                if collecting and len(line) > 5:
                                    # Türkçe karakter veya yasal terim içeren satırları öncelikle al
                                    if (any(char in line for char in 'çğıöşüÇĞIİÖŞÜ') or
                                        any(term in line.lower() for term in ['madde', 'kanun', 'hukuk', 'dava', 'karar', 'mahkeme'])):
                                        karar_lines.append(line)
                                    elif len(line) > 15:  # Uzun satırları da al
                                        karar_lines.append(line)
                            
                            # Yeterli içerik bulunduysa döndür
                            if len(karar_lines) > 5:
                                best_text = '\n'.join(karar_lines)
                                best_source = f"UYAP getDokuman parsing - {strategy_name}"
                                logger.info(f"Deneme {attempt}: UYAP getDokuman URL'sinden metin alındı ({strategy_name}) - {len(best_text)} karakter")
                                break
                        
                        # Hiç strateji işe yaramazsa, raw içeriği döndür
                        if not best_text and len(full_text) > 100:
                            best_text = full_text[:3000]  # İlk 3000 karakter
                            best_source = "UYAP getDokuman raw fallback"
                            logger.info(f"Deneme {attempt}: UYAP getDokuman raw fallback - {len(best_text)} karakter")
                    else:
                        # Diğer URL'ler için normal selector parsing
                        # Çoklu selector deneme - UYAP Emsal spesifik
                        selectors_groups = [
                            # UYAP PrimeFaces spesifik selectorlar
                            ["div.ui-panel-content", "div.ui-widget-content", "div.ui-outputpanel", "span.ui-outputlabel"],
                            # UYAP karar spesifik selectorlar
                            ["div.karar-metni", "div.karar-icerik", "div.karar-detay", "div.icerik"],
                            # JSF ve PrimeFaces ID'li elementler
                            ["div[id*='detay']", "div[id*='icerik']", "div[id*='karar']", "div[id*='panel']"],
                            # Tablo yapısı selectorları
                            ["table.karar-tablosu", "table.ui-datatable", "td.karar-cell", "tr.karar-row"],
                            # Genel content selectorlar
                            ["div[class*='content']", "div[class*='karar']", "div[class*='detay']", "div[class*='bilgi']"],
                            # Pre ve text elementleri
                            ["pre", "div.text-content", "span.text", "p.karar-paragraf"],
                            # Bootstrap ve genel selectorlar
                            ["div.container", "div.content", "div.main-content", "article"],
                            # Son çare selectorlar
                            ["main", "section", ".container", ".content", "body"]
                        ]
                        
                        for group_idx, selectors in enumerate(selectors_groups):
                            for selector in selectors:
                                elements = soup.select(selector)
                                for element in elements:
                                    text = element.get_text(separator='\n', strip=True)
                                    # UYAP Emsal için özel kriterler
                                    if (len(text) > len(best_text) and 
                                        len(text) > 150 and
                                        any(keyword in text.lower() for keyword in ['karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'esas', 'sonuç', 'emsal', 'uyap', 'türkiye', 'cumhuriyet', 'adalet', 'kanun', 'madde', 'fıkra'])):
                                        best_text = text
                                        best_source = f"Group {group_idx+1}, Selector: {selector}"
                                        logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                    
                    # Eğer spesifik selector bulamazsa, akıllı body parsing
                    if len(best_text) < 300 and soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        
                        # UYAP sayfalarında karar metnini bul
                        lines = body_text.split('\n')
                        filtered_lines = []
                        skip_keywords = [
                            'menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 
                            'giriş', 'çıkış', 'uyap', 'bilgi bankası', 'primetime', 'primefaces',
                            'anasayfa', 'ana sayfa', 'sitemap', 'site haritası', 'yardım', 'help',
                            'copyright', 'telif', 'version', 'sürüm'
                        ]
                        
                        karar_started = False
                        for line in lines:
                            line = line.strip()
                            
                            # Karar başlangıcını tespit et
                            if any(start_keyword in line.lower() for start_keyword in ['karar', 'hüküm', 'gerekçe', 'dava', 'esas']):
                                karar_started = True
                            
                            if (karar_started and len(line) > 10 and 
                                not any(skip in line.lower() for skip in skip_keywords) and
                                not line.startswith('http') and
                                not (line.isdigit() and len(line) < 10) and
                                not line.startswith('javascript:') and
                                not line.startswith('function(')):
                                filtered_lines.append(line)
                        
                        if len(filtered_lines) > 5:  # En az 5 satır varsa
                            best_text = '\n'.join(filtered_lines)
                            best_source = "Smart body parsing"
                            logger.info(f"Deneme {attempt}: Akıllı body parsing ile metin alındı - {len(best_text)} karakter")
                    
                    # Metni temizle - hafif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Eğer temizleme sonrası metin çok kısaldıysa, orijinal metni kullan
                    if len(cleaned_text) < 100 and len(best_text) > 1000:
                        logger.warning(f"Emsal: Temizleme çok agresif oldu ({len(cleaned_text)} < 100 ama orijinal {len(best_text)}), orijinal metin kullanılıyor")
                        cleaned_text = best_text[:5000]  # İlk 5000 karakteri al
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:  # Daha düşük minimum
                        logger.info(f"Emsal metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'emsal',
                            'extraction_method': f"Attempt {attempt} - {best_source} ({method_name})"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                        
                except Exception as e:
                    logger.error(f"Deneme {attempt} hatası: {e}")
                    continue
        
        # Tüm denemeler başarısız oldu - son çare olarak orijinal URL ile yönlendirme
        original_url = url_formats[0]
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'redirect_url': original_url, 
            'source_url': original_url, 
            'court_type': 'emsal',
            'error_info': 'Tüm extraction yöntemleri başarısız oldu'
        }

    async def _get_anayasa_document_content(self, document_id: str) -> Dict[str, Any]:
        """Anayasa Mahkemesi kararının tam içeriğini çoklu yöntemle getirir - Yargıtay benzeri gelişmiş sistem."""
        
        # Farklı URL formatlarını dene
        url_formats = [
            f"https://normkararlarbilgibankasi.anayasa.gov.tr/Karar/Goster/{document_id}",
            f"https://www.anayasa.gov.tr/icsayfalar/kararlar/kararlarbilgibankasi/karar_detay.html?id={document_id}",
            f"https://kararlarbilgibankasi.anayasa.gov.tr/detay/{document_id}",
            f"https://www.anayasa.gov.tr/Kararlar/Detay/{document_id}",
            f"https://normkararlarbilgibankasi.anayasa.gov.tr/Norm_Kilavuz.pdf?id={document_id}"
        ]
        
        # Farklı scraping yöntemleri
        scraping_methods = [
            ('normal', self.http_manager.get_content),
            ('different_agents', self.http_manager.get_content_with_different_agents),
            ('session_retry', self.http_manager.get_content_with_session_retry)
        ]
        
        for url_idx, source_url in enumerate(url_formats):
            for method_idx, (method_name, method_func) in enumerate(scraping_methods):
                attempt = (url_idx * len(scraping_methods)) + method_idx + 1
                total_attempts = len(url_formats) * len(scraping_methods)
                
                try:
                    logger.info(f"Anayasa Mahkemesi karar metni deneme {attempt}/{total_attempts}: {source_url} ({method_name})")
                    
                    # HTTP isteği ile sayfayı çek
                    response = method_func(source_url, timeout=25)
                    if not response:
                        logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                        continue
                    
                    # PDF kontrolü
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        logger.info(f"Deneme {attempt}: PDF bulundu")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'anayasa',
                            'extraction_method': f"PDF - {method_name}"
                        }
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Gereksiz elementleri kaldır
                    for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select", "noscript"]):
                        element.decompose()
                    
                    # Çoklu selector deneme - Anayasa Mahkemesi spesifik
                    selectors_groups = [
                        # Anayasa Mahkemesi spesifik selectorlar
                        ["div.karar-detay", "div.karar-metni", "div.karar-icerik", "div.norm-detay"],
                        # Genel content selectorlar
                        ["div[class*='content']", "div[class*='karar']", "div[class*='detay']", "div[class*='norm']"],
                        # Tablo ve liste selectorlar
                        ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                        # Bootstrap ve genel selectorlar
                        ["div.container", "div.content", "div.main-content", "article"],
                        # Fallback selectorlar
                        ["main", "section", ".container", ".content"]
                    ]
                    
                    best_text = ""
                    best_source = ""
                    
                    for group_idx, selectors in enumerate(selectors_groups):
                        for selector in selectors:
                            elements = soup.select(selector)
                            for element in elements:
                                text = element.get_text(separator='\n', strip=True)
                                
                                # Anayasa Mahkemesi için özel kriterler
                                if (len(text) > len(best_text) and 
                                    len(text) > 150 and
                                    (any(keyword in text.lower() for keyword in ['anayasa', 'karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'norm', 'denetim']) or
                                     len(text) > 1000)):
                                    best_text = text
                                    best_source = f"Group {group_idx+1}, Selector: {selector}"
                                    logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                    
                    # Eğer spesifik selector bulamazsa, body'den al
                    if len(best_text) < 400 and soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        lines = body_text.split('\n')
                        filtered_lines = []
                        skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış', 'anayasa.gov.tr']
                        
                        for line in lines:
                            line = line.strip()
                            if (len(line) > 10 and
                                not any(skip in line.lower() for skip in skip_keywords) and
                                not line.startswith('http') and
                                not line.isdigit() and
                                not re.match(r'^[\s\.\-\,]+$', line)):
                                filtered_lines.append(line)
                        
                        if len(filtered_lines) > 5:
                            best_text = '\n'.join(filtered_lines)
                            best_source = "Body fallback enhanced"
                            logger.info(f"Deneme {attempt}: Body'den metin alındı - {len(best_text)} karakter")
                    
                    # Metni temizle - hafif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:
                        logger.info(f"Anayasa Mahkemesi metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'anayasa',
                            'extraction_method': f"Attempt {attempt} - {best_source} ({method_name})"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                        
                except Exception as e:
                    logger.error(f"Deneme {attempt} hatası: {e}")
                    continue
        
        # Tüm denemeler başarısız oldu - son çare olarak yönlendirme
        original_url = url_formats[0]
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'content': f"""
            <div class="alert alert-warning">
                <h5><i class="fas fa-exclamation-triangle"></i> Karar Detayına Yönlendirme</h5>
                <p class="mb-3">Karar metni otomatik olarak çekilemedi. Manuel olarak görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                <a href="{original_url}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i> UYAP Emsal Karar Metnini Görüntüle
                </a>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i> Tüm extraction yöntemleri denendi ancak başarısız oldu.
                    </small>
                </div>
            </div>
            """,
            'content_type': 'text',
            'source_url': original_url,
            'court_type': 'emsal'
        }

    async def _get_uyusmazlik_document_content(self, document_id: str) -> Dict[str, Any]:
        """Uyuşmazlık Mahkemesi kararının tam içeriğini çoklu yöntemle getirir - Yargıtay benzeri gelişmiş sistem."""
        
        # Farklı URL formatlarını dene
        url_formats = [
            f"https://kararlar.uyusmazlik.gov.tr/Karar/Detay/{document_id}",
            f"https://www.uyusmazlik.gov.tr/Kararlar/Detay/{document_id}",
            f"https://kararlar.uyusmazlik.gov.tr/detay/{document_id}",
            f"https://www.uyusmazlik.gov.tr/karar/{document_id}",
            f"https://kararlar.uyusmazlik.gov.tr/api/karar/{document_id}"
        ]
        
        # Farklı scraping yöntemleri
        scraping_methods = [
            ('normal', self.http_manager.get_content),
            ('different_agents', self.http_manager.get_content_with_different_agents),
            ('session_retry', self.http_manager.get_content_with_session_retry)
        ]
        
        for url_idx, source_url in enumerate(url_formats):
            for method_idx, (method_name, method_func) in enumerate(scraping_methods):
                attempt = (url_idx * len(scraping_methods)) + method_idx + 1
                total_attempts = len(url_formats) * len(scraping_methods)
                
                try:
                    logger.info(f"Uyuşmazlık Mahkemesi karar metni deneme {attempt}/{total_attempts}: {source_url} ({method_name})")
                    
                    # HTTP isteği ile sayfayı çek
                    response = method_func(source_url, timeout=25)
                    if not response:
                        logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                        continue
                    
                    # PDF kontrolü
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        logger.info(f"Deneme {attempt}: PDF bulundu")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'uyusmazlik',
                            'extraction_method': f"PDF - {method_name}"
                        }
                    
                    # JSON API response kontrolü
                    if 'json' in content_type:
                        try:
                            json_data = response.json()
                            if 'content' in json_data or 'text' in json_data or 'karar' in json_data:
                                content = json_data.get('content') or json_data.get('text') or json_data.get('karar', '')
                                if len(content) > 200:
                                    logger.info(f"Deneme {attempt}: JSON API'den içerik alındı")
                                    return {
                                        'success': True, 
                                        'content': content, 
                                        'content_type': 'text', 
                                        'source_url': source_url, 
                                        'court_type': 'uyusmazlik',
                                        'extraction_method': f"JSON API - {method_name}"
                                    }
                        except:
                            pass
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Gereksiz elementleri kaldır
                    for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select", "noscript"]):
                        element.decompose()
                    
                    # Çoklu selector deneme - Uyuşmazlık Mahkemesi spesifik
                    selectors_groups = [
                        # Uyuşmazlık Mahkemesi spesifik selectorlar
                        ["div.karar-detay", "div.karar-metni", "div.karar-icerik", "div.uyusmazlik-karar"],
                        # Genel content selectorlar
                        ["div[class*='content']", "div[class*='karar']", "div[class*='detay']", "div[class*='uyusmazlik']"],
                        # Tablo ve liste selectorlar
                        ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                        # Bootstrap ve genel selectorlar
                        ["div.container", "div.content", "div.main-content", "article"],
                        # Fallback selectorlar
                        ["main", "section", ".container", ".content"]
                    ]
                    
                    best_text = ""
                    best_source = ""
                    
                    for group_idx, selectors in enumerate(selectors_groups):
                        for selector in selectors:
                            elements = soup.select(selector)
                            for element in elements:
                                text = element.get_text(separator='\n', strip=True)
                                
                                # Uyuşmazlık Mahkemesi için özel kriterler
                                if (len(text) > len(best_text) and 
                                    len(text) > 150 and
                                    (any(keyword in text.lower() for keyword in ['uyuşmazlık', 'karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'esas', 'sonuç']) or
                                     len(text) > 1000)):
                                    best_text = text
                                    best_source = f"Group {group_idx+1}, Selector: {selector}"
                                    logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                    
                    # Eğer spesifik selector bulamazsa, body'den al
                    if len(best_text) < 400 and soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        lines = body_text.split('\n')
                        filtered_lines = []
                        skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış', 'uyusmazlik.gov.tr']
                        
                        for line in lines:
                            line = line.strip()
                            if (len(line) > 10 and
                                not any(skip in line.lower() for skip in skip_keywords) and
                                not line.startswith('http') and
                                not line.isdigit() and
                                not re.match(r'^[\s\.\-\,]+$', line)):
                                filtered_lines.append(line)
                        
                        if len(filtered_lines) > 5:
                            best_text = '\n'.join(filtered_lines)
                            best_source = "Body fallback enhanced"
                            logger.info(f"Deneme {attempt}: Body'den metin alındı - {len(best_text)} karakter")
                    
                    # Metni temizle - hafif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:
                        logger.info(f"Uyuşmazlık Mahkemesi metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'uyusmazlik',
                            'extraction_method': f"Attempt {attempt} - {best_source} ({method_name})"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                        
                except Exception as e:
                    logger.error(f"Deneme {attempt} hatası: {e}")
                    continue
        
        # Tüm denemeler başarısız oldu - son çare olarak yönlendirme
        original_url = url_formats[0]
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'content': f"""
            <div class="alert alert-warning">
                <h5><i class="fas fa-exclamation-triangle"></i> Karar Detayına Yönlendirme</h5>
                <p class="mb-3">Karar metni otomatik olarak çekilemedi. Manuel olarak görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                <a href="{original_url}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i> Uyuşmazlık Mahkemesi Karar Metnini Görüntüle
                </a>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i> Tüm extraction yöntemleri denendi ancak başarısız oldu.
                    </small>
                </div>
            </div>
            """,
            'content_type': 'text',
            'source_url': original_url,
            'court_type': 'uyusmazlik'
        }

    async def _get_kik_document_content(self, document_id: str) -> Dict[str, Any]:
        """KİK kararının tam içeriğini çoklu yöntemle getirir - Yargıtay benzeri gelişmiş sistem."""
        
        # Farklı URL formatlarını dene
        url_formats = [
            f"https://www.kik.gov.tr/Kararlar/Detay/{document_id}",
            f"https://kik.gov.tr/Kararlar/Detay/{document_id}",
            f"https://www.kik.gov.tr/karar/{document_id}",
            f"https://kik.gov.tr/karar/{document_id}",
            f"https://www.kik.gov.tr/api/karar/{document_id}"
        ]
        
        # Farklı scraping yöntemleri
        scraping_methods = [
            ('normal', self.http_manager.get_content),
            ('different_agents', self.http_manager.get_content_with_different_agents),
            ('session_retry', self.http_manager.get_content_with_session_retry)
        ]
        
        for url_idx, source_url in enumerate(url_formats):
            for method_idx, (method_name, method_func) in enumerate(scraping_methods):
                attempt = (url_idx * len(scraping_methods)) + method_idx + 1
                total_attempts = len(url_formats) * len(scraping_methods)
                
                try:
                    logger.info(f"KİK karar metni deneme {attempt}/{total_attempts}: {source_url} ({method_name})")
                    
                    # HTTP isteği ile sayfayı çek
                    response = method_func(source_url, timeout=25)
                    if not response:
                        logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                        continue
                    
                    # PDF kontrolü
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        logger.info(f"Deneme {attempt}: PDF bulundu")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'kik',
                            'extraction_method': f"PDF - {method_name}"
                        }
                    
                    # JSON API response kontrolü
                    if 'json' in content_type:
                        try:
                            json_data = response.json()
                            if 'content' in json_data or 'text' in json_data or 'karar' in json_data:
                                content = json_data.get('content') or json_data.get('text') or json_data.get('karar', '')
                                if len(content) > 200:
                                    logger.info(f"Deneme {attempt}: JSON API'den içerik alındı")
                                    return {
                                        'success': True, 
                                        'content': content, 
                                        'content_type': 'text', 
                                        'source_url': source_url, 
                                        'court_type': 'kik',
                                        'extraction_method': f"JSON API - {method_name}"
                                    }
                        except:
                            pass
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Gereksiz elementleri kaldır
                    for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select", "noscript"]):
                        element.decompose()
                    
                    # Çoklu selector deneme - KİK spesifik
                    selectors_groups = [
                        # KİK spesifik selectorlar
                        ["div.karar-detay", "div.karar-metni", "div.karar-icerik", "div.kik-karar"],
                        # Genel content selectorlar
                        ["div[class*='content']", "div[class*='karar']", "div[class*='detay']", "div[class*='kik']"],
                        # Tablo ve liste selectorlar
                        ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                        # Bootstrap ve genel selectorlar
                        ["div.container", "div.content", "div.main-content", "article"],
                        # Fallback selectorlar
                        ["main", "section", ".container", ".content"]
                    ]
                    
                    best_text = ""
                    best_source = ""
                    
                    for group_idx, selectors in enumerate(selectors_groups):
                        for selector in selectors:
                            elements = soup.select(selector)
                            for element in elements:
                                text = element.get_text(separator='\n', strip=True)
                                
                                # KİK için özel kriterler
                                if (len(text) > len(best_text) and 
                                    len(text) > 150 and
                                    (any(keyword in text.lower() for keyword in ['kik', 'kamu', 'ihale', 'karar', 'hüküm', 'gerekçe', 'kurum', 'dava', 'esas', 'sonuç']) or
                                     len(text) > 1000)):
                                    best_text = text
                                    best_source = f"Group {group_idx+1}, Selector: {selector}"
                                    logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                    
                    # Eğer spesifik selector bulamazsa, body'den al
                    if len(best_text) < 400 and soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        lines = body_text.split('\n')
                        filtered_lines = []
                        skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış', 'kik.gov.tr']
                        
                        for line in lines:
                            line = line.strip()
                            if (len(line) > 10 and
                                not any(skip in line.lower() for skip in skip_keywords) and
                                not line.startswith('http') and
                                not line.isdigit() and
                                not re.match(r'^[\s\.\-\,]+$', line)):
                                filtered_lines.append(line)
                        
                        if len(filtered_lines) > 5:
                            best_text = '\n'.join(filtered_lines)
                            best_source = "Body fallback enhanced"
                            logger.info(f"Deneme {attempt}: Body'den metin alındı - {len(best_text)} karakter")
                    
                    # Metni temizle - hafif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:
                        logger.info(f"KİK metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'kik',
                            'extraction_method': f"Attempt {attempt} - {best_source} ({method_name})"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                        
                except Exception as e:
                    logger.error(f"Deneme {attempt} hatası: {e}")
                    continue
        
        # Tüm denemeler başarısız oldu - son çare olarak yönlendirme
        original_url = url_formats[0]
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'content': f"""
            <div class="alert alert-warning">
                <h5><i class="fas fa-exclamation-triangle"></i> Karar Detayına Yönlendirme</h5>
                <p class="mb-3">Karar metni otomatik olarak çekilemedi. Manuel olarak görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                <a href="{original_url}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i> Kamu İhale Kurumu Karar Metnini Görüntüle
                </a>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i> Tüm extraction yöntemleri denendi ancak başarısız oldu.
                    </small>
                </div>
            </div>
            """,
            'content_type': 'text',
            'source_url': original_url,
            'court_type': 'kik'
        }

    async def _get_rekabet_document_content(self, document_url: str) -> Dict[str, Any]:
        """Rekabet Kurumu kararının tam içeriğini çoklu yöntemle getirir - Yargıtay benzeri gelişmiş sistem."""
        
        # Farklı URL formatlarını dene - document_url'den document_id çıkarılabilir
        base_urls = []
        if document_url:
            base_urls.append(document_url)
            # URL'den ID çıkarmaya çalış
            if 'id=' in document_url:
                doc_id = document_url.split('id=')[-1].split('&')[0]
            elif '/' in document_url:
                doc_id = document_url.split('/')[-1]
            else:
                doc_id = document_url
        else:
            doc_id = "default"
        
        url_formats = base_urls + [
            f"https://www.rekabet.gov.tr/Karar/Detay/{doc_id}",
            f"https://rekabet.gov.tr/Karar/Detay/{doc_id}",
            f"https://www.rekabet.gov.tr/karar/{doc_id}",
            f"https://rekabet.gov.tr/karar/{doc_id}",
            f"https://www.rekabet.gov.tr/api/karar/{doc_id}"
        ]
        
        # Farklı scraping yöntemleri
        scraping_methods = [
            ('normal', self.http_manager.get_content),
            ('different_agents', self.http_manager.get_content_with_different_agents),
            ('session_retry', self.http_manager.get_content_with_session_retry)
        ]
        
        for url_idx, source_url in enumerate(url_formats):
            for method_idx, (method_name, method_func) in enumerate(scraping_methods):
                attempt = (url_idx * len(scraping_methods)) + method_idx + 1
                total_attempts = len(url_formats) * len(scraping_methods)
                
                try:
                    logger.info(f"Rekabet Kurumu karar metni deneme {attempt}/{total_attempts}: {source_url} ({method_name})")
                    
                    # HTTP isteği ile sayfayı çek
                    response = method_func(source_url, timeout=25)
                    if not response:
                        logger.warning(f"Deneme {attempt}: Sayfa yüklenemedi")
                        continue
                    
                    # PDF kontrolü
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        logger.info(f"Deneme {attempt}: PDF bulundu")
                        return {
                            'success': True, 
                            'content_type': 'pdf', 
                            'pdf_url': source_url, 
                            'source_url': source_url, 
                            'court_type': 'rekabet',
                            'extraction_method': f"PDF - {method_name}"
                        }
                    
                    # JSON API response kontrolü
                    if 'json' in content_type:
                        try:
                            json_data = response.json()
                            if 'content' in json_data or 'text' in json_data or 'karar' in json_data:
                                content = json_data.get('content') or json_data.get('text') or json_data.get('karar', '')
                                if len(content) > 200:
                                    logger.info(f"Deneme {attempt}: JSON API'den içerik alındı")
                                    return {
                                        'success': True, 
                                        'content': content, 
                                        'content_type': 'text', 
                                        'source_url': source_url, 
                                        'court_type': 'rekabet',
                                        'extraction_method': f"JSON API - {method_name}"
                                    }
                        except:
                            pass
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Gereksiz elementleri kaldır
                    for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select", "noscript"]):
                        element.decompose()
                    
                    # Çoklu selector deneme - Rekabet Kurumu spesifik
                    selectors_groups = [
                        # Rekabet Kurumu spesifik selectorlar
                        ["div.karar-detay", "div.karar-metni", "div.karar-icerik", "div.rekabet-karar"],
                        # Genel content selectorlar
                        ["div[class*='content']", "div[class*='karar']", "div[class*='detay']", "div[class*='rekabet']"],
                        # Tablo ve liste selectorlar
                        ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                        # Bootstrap ve genel selectorlar
                        ["div.container", "div.content", "div.main-content", "article"],
                        # Fallback selectorlar
                        ["main", "section", ".container", ".content"]
                    ]
                    
                    best_text = ""
                    best_source = ""
                    
                    for group_idx, selectors in enumerate(selectors_groups):
                        for selector in selectors:
                            elements = soup.select(selector)
                            for element in elements:
                                text = element.get_text(separator='\n', strip=True)
                                
                                # Rekabet Kurumu için özel kriterler
                                if (len(text) > len(best_text) and 
                                    len(text) > 150 and
                                    (any(keyword in text.lower() for keyword in ['rekabet', 'kurul', 'karar', 'hüküm', 'gerekçe', 'inceleme', 'dava', 'esas', 'sonuç']) or
                                     len(text) > 1000)):
                                    best_text = text
                                    best_source = f"Group {group_idx+1}, Selector: {selector}"
                                    logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                    
                    # Eğer spesifik selector bulamazsa, body'den al
                    if len(best_text) < 400 and soup.body:
                        body_text = soup.body.get_text(separator='\n', strip=True)
                        lines = body_text.split('\n')
                        filtered_lines = []
                        skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış', 'rekabet.gov.tr']
                        
                        for line in lines:
                            line = line.strip()
                            if (len(line) > 10 and
                                not any(skip in line.lower() for skip in skip_keywords) and
                                not line.startswith('http') and
                                not line.isdigit() and
                                not re.match(r'^[\s\.\-\,]+$', line)):
                                filtered_lines.append(line)
                        
                        if len(filtered_lines) > 5:
                            best_text = '\n'.join(filtered_lines)
                            best_source = "Body fallback enhanced"
                            logger.info(f"Deneme {attempt}: Body'den metin alındı - {len(best_text)} karakter")
                    
                    # Metni temizle - hafif filtreleme
                    cleaned_text = self._clean_decision_text_light(best_text)
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 100:
                        logger.info(f"Rekabet Kurumu metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                        return {
                            'success': True, 
                            'content': cleaned_text, 
                            'content_type': 'text', 
                            'source_url': source_url, 
                            'court_type': 'rekabet',
                            'extraction_method': f"Attempt {attempt} - {best_source} ({method_name})"
                        }
                    else:
                        logger.warning(f"Deneme {attempt}: Metin çok kısa - {len(cleaned_text)} karakter")
                        
                except Exception as e:
                    logger.error(f"Deneme {attempt} hatası: {e}")
                    continue
        
        # Tüm denemeler başarısız oldu - son çare olarak yönlendirme
        original_url = url_formats[0] if url_formats else "https://www.rekabet.gov.tr/tr/Kararlar"
        logger.error(f"Tüm denemeler başarısız oldu, yönlendirme yapılacak: {original_url}")
        return {
            'success': True, 
            'content': f"""
            <div class="alert alert-warning">
                <h5><i class="fas fa-exclamation-triangle"></i> Karar Detayına Yönlendirme</h5>
                <p class="mb-3">Karar metni otomatik olarak çekilemedi. Manuel olarak görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                <a href="{original_url}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i> Rekabet Kurumu Karar Metnini Görüntüle
                </a>
                <div class="mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i> Tüm extraction yöntemleri denendi ancak başarısız oldu.
                    </small>
                </div>
            </div>
            """,
            'content_type': 'text',
            'source_url': original_url,
            'court_type': 'rekabet'
        }

    async def close_all_clients(self):
        """Tüm client'ları kapat"""
        try:
            await self.yargitay_client.close_client_session()
            await self.danistay_client.close_client_session()
            await self.emsal_client.close_client_session()
            await self.anayasa_client.close_client_session()
            await self.uyusmazlik_client.close_client_session()
            await self.kik_client.close_client_session()
            await self.rekabet_client.close_client_session()
            # HTTP session'ı kapat
            if hasattr(self.http_manager.session, 'close'):
                self.http_manager.session.close()
            logger.info("Tüm client'lar kapatıldı")
        except Exception as e:
            logger.error(f"Client'lar kapatılırken hata: {e}")

# Global instance
yargi_integration = YargiFlaskIntegration()

# Flask için wrapper fonksiyonlar
def search_yargi_kararlari(keyword: str,
                          court_type: str = "all",
                          court_unit: str = "",
                          case_year: str = "",
                          decision_year: str = "",
                          start_date: str = "",
                          end_date: str = "",
                          page_number: int = 1,
                          page_size: int = 20) -> Dict[str, Any]:
    """Flask için yargi kararları arama fonksiyonu"""
    return yargi_integration.search_all_courts(
        keyword=keyword,
        court_type=court_type,
        court_unit=court_unit,
        case_year=case_year,
        decision_year=decision_year,
        start_date=start_date,
        end_date=end_date,
        page_number=page_number,
        page_size=page_size
    )

def get_court_options() -> Dict[str, List[Dict[str, str]]]:
    """Flask için mahkeme seçenekleri fonksiyonu"""
    return yargi_integration.get_court_options()

def get_document_content(court_type: str, document_id: str, document_url: str = None) -> Dict[str, Any]:
    """Belirli bir kararın tam içeriğini getir - MCP client'larının doğru fonksiyonlarını kullanarak"""
    try:
        # Global attribute'lar için başlangıç değerleri
        if not hasattr(get_document_content, '_last_danistay_keyword'):
            get_document_content._last_danistay_keyword = ''
            
        # Event loop oluştur
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        logger.info(f"Doküman içeriği istendi: court_type={court_type}, document_id={document_id}")
        
        if court_type == "yargitay":
            # Yargıtay için unified modülden client oluştur (event loop sorunu nedeniyle)
            client = YargitayOfficialApiClient()
            
            try:
                result = loop.run_until_complete(
                    client.get_decision_document_as_markdown(document_id)
                )
                
                if result and result.markdown_content:
                    logger.info(f"Yargıtay markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                    return {
                        'success': True,
                        'content': result.markdown_content,
                        'content_type': 'text',
                        'source_url': str(result.source_url) if result.source_url else '',
                        'court_type': 'yargitay',
                        'extraction_method': 'MCP Client API'
                    }
                else:
                    logger.warning("Yargıtay markdown içeriği boş")
                    # Fallback olarak web scraping dene
                    return loop.run_until_complete(
                        yargi_integration._get_yargitay_document_content(document_id)
                    )
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
                
        elif court_type == "danistay":
            # Danıştay için unified modülden client oluştur
            client = DanistayApiClient()
            
            try:
                # Danıştay için aranan kelimeyi de gönder
                # Global değişkenden veya session'dan al
                aranan_kelime = getattr(get_document_content, '_last_danistay_keyword', '')
                result = loop.run_until_complete(
                    client.get_decision_document_as_markdown(document_id, aranan_kelime)
                )
                
                if result and result.markdown_content:
                    logger.info(f"Danıştay markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                    return {
                        'success': True,
                        'content': result.markdown_content,
                        'content_type': 'text',
                        'source_url': str(result.source_url) if result.source_url else '',
                        'court_type': 'danistay',
                        'extraction_method': 'MCP Client API'
                    }
                else:
                    logger.warning("Danıştay markdown içeriği boş")
                    # Fallback olarak web scraping dene
                    return loop.run_until_complete(
                        yargi_integration._get_danistay_document_content(document_id)
                    )
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
                
        elif court_type == "emsal":
            # Emsal için unified modülden client oluştur
            client = EmsalApiClient()
            
            try:
                result = loop.run_until_complete(
                    client.get_decision_document_as_markdown(document_id)
                )
                
                if result and result.markdown_content:
                    logger.info(f"Emsal markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                    return {
                        'success': True,
                        'content': result.markdown_content,
                        'content_type': 'text',
                        'source_url': str(result.source_url) if result.source_url else '',
                        'court_type': 'emsal',
                        'extraction_method': 'MCP Client API'
                    }
                else:
                    logger.warning("Emsal markdown içeriği boş")
                    # Fallback olarak web scraping dene
                    return loop.run_until_complete(
                        yargi_integration._get_emsal_document_content(document_id)
                    )
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
                
        elif court_type == "anayasa":
            # Anayasa Mahkemesi için unified modülden client oluştur
            client = AnayasaMahkemesiApiClient()
            
            try:
                # document_url'den path çıkar
                document_path = document_url
                if document_url and document_url.startswith('http'):
                    # URL'den path kısmını çıkar
                    from urllib.parse import urlparse
                    parsed = urlparse(document_url)
                    document_path = parsed.path
                
                # Anayasa için basit get_decision_document_as_markdown kullan
                if hasattr(client, 'get_decision_document_as_markdown'):
                    result = loop.run_until_complete(
                        client.get_decision_document_as_markdown(document_id)
                    )
                    
                    if result and result.markdown_content:
                        logger.info(f"Anayasa Mahkemesi markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                        return {
                            'success': True,
                            'content': result.markdown_content,
                            'content_type': 'text',
                            'source_url': str(result.source_url) if result.source_url else '',
                            'court_type': 'anayasa',
                            'extraction_method': 'MCP Client API'
                        }
                    else:
                        logger.warning("Anayasa Mahkemesi markdown içeriği boş")
                else:
                    logger.warning("Anayasa MCP Client'ında get_decision_document_as_markdown metodu bulunamadı")
                
                # Fallback olarak web scraping dene
                return loop.run_until_complete(
                    yargi_integration._get_anayasa_document_content(document_id)
                )
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
                
        elif court_type == "uyusmazlik":
            # Uyuşmazlık Mahkemesi için unified modülden client oluştur
            client = UyusmazlikApiClient()
            
            try:
                if not document_url:
                    # URL yoksa fallback
                    return loop.run_until_complete(
                        yargi_integration._get_uyusmazlik_document_content(document_id)
                    )
                
                # Yeni get_decision_document_as_markdown metodunu kullan
                result = loop.run_until_complete(
                    client.get_decision_document_as_markdown(document_url)
                )
                
                if result and result.markdown_content and not result.markdown_content.startswith("Hata:"):
                    logger.info(f"Uyuşmazlık Mahkemesi markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                    return {
                        'success': True,
                        'content': result.markdown_content,
                        'content_type': 'text',
                        'source_url': str(result.source_url) if result.source_url else '',
                        'court_type': 'uyusmazlik',
                        'extraction_method': 'MCP Client API'
                    }
                else:
                    logger.warning("Uyuşmazlık Mahkemesi markdown içeriği boş veya hatalı")
                    # Fallback olarak web scraping dene
                    return loop.run_until_complete(
                        yargi_integration._get_uyusmazlik_document_content(document_id)
                    )
                
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
                
        elif court_type == "kik":
            # KİK için unified modülden client oluştur
            client = KikApiClient()
            
            try:
                # MCP Client'ın get_decision_document_as_markdown metodunu kullan
                if hasattr(client, 'get_decision_document_as_markdown'):
                    result = loop.run_until_complete(
                        client.get_decision_document_as_markdown(document_id)
                    )
                    
                    if result and result.markdown_chunk:
                        logger.info(f"KİK markdown içeriği başarıyla alındı: {len(result.markdown_chunk)} karakter")
                        return {
                            'success': True,
                            'content': result.markdown_chunk,
                            'content_type': 'text',
                            'source_url': str(result.source_url) if result.source_url else '',
                            'court_type': 'kik',
                            'extraction_method': 'MCP Client API'
                        }
                    else:
                        logger.warning("KİK markdown içeriği boş")
                else:
                    logger.warning("KİK MCP Client'ında get_decision_document_as_markdown metodu bulunamadı")
                
                # Fallback olarak web scraping dene
                return loop.run_until_complete(
                    yargi_integration._get_kik_document_content(document_id)
                )
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
                
        elif court_type == "rekabet":
            # Rekabet Kurumu için unified modülden client oluştur
            client = RekabetKurumuApiClient()
            
            try:
                # MCP Client'ın get_decision_document_as_markdown metodunu kullan
                if hasattr(client, 'get_decision_document_as_markdown'):
                    result = loop.run_until_complete(
                        client.get_decision_document_as_markdown(document_id)
                    )
                    
                    if result and isinstance(result, str):
                        logger.info(f"Rekabet Kurumu markdown içeriği başarıyla alındı: {len(result)} karakter")
                        return {
                            'success': True,
                            'content': result,
                            'content_type': 'text',
                            'source_url': f"https://www.rekabet.gov.tr/Karar?kararId={document_id}",
                            'court_type': 'rekabet',
                            'extraction_method': 'MCP Client API'
                        }
                    else:
                        logger.warning("Rekabet Kurumu markdown içeriği boş")
                else:
                    logger.warning("Rekabet MCP Client'ında get_decision_document_as_markdown metodu bulunamadı")
                
                # Fallback olarak web scraping dene
                return loop.run_until_complete(
                    yargi_integration._get_rekabet_document_content(document_url or document_id)
                )
            finally:
                # Client'ı kapat
                try:
                    loop.run_until_complete(client.close_client_session())
                except:
                    pass
        else:
            return {
                'success': False,
                'error': f'Desteklenmeyen mahkeme türü: {court_type}'
            }
        
    except Exception as e:
        logger.error(f"Doküman içeriği alınırken hata ({court_type}): {e}")
        
        # Hata durumunda fallback olarak web scraping dene
        try:
            loop = asyncio.get_event_loop()
            if court_type == "yargitay":
                return loop.run_until_complete(
                    yargi_integration._get_yargitay_document_content(document_id)
                )
            elif court_type == "danistay":
                return loop.run_until_complete(
                    yargi_integration._get_danistay_document_content(document_id)
                )
            elif court_type == "emsal":
                return loop.run_until_complete(
                    yargi_integration._get_emsal_document_content(document_id)
                )
            elif court_type == "anayasa":
                return loop.run_until_complete(
                    yargi_integration._get_anayasa_document_content(document_id)
                )
            elif court_type == "uyusmazlik":
                return loop.run_until_complete(
                    yargi_integration._get_uyusmazlik_document_content(document_id)
                )
            elif court_type == "kik":
                return loop.run_until_complete(
                    yargi_integration._get_kik_document_content(document_id)
                )
            elif court_type == "rekabet":
                return loop.run_until_complete(
                    yargi_integration._get_rekabet_document_content(document_url or document_id)
                )
            else:
                # Bilinmeyen mahkeme türü için generic fallback
                fallback_url = document_url or f"https://www.{court_type}.gov.tr"
                court_names = {
                    'anayasa': 'Anayasa Mahkemesi',
                    'danistay': 'Danıştay',
                    'emsal': 'UYAP Emsal',
                    'uyusmazlik': 'Uyuşmazlık Mahkemesi',
                    'kik': 'Kamu İhale Kurumu',
                    'rekabet': 'Rekabet Kurumu'
                }
                court_display_name = court_names.get(court_type, court_type.title())
                
                return {
                    'success': True,
                    'content': f"""
                    <div class="alert alert-warning">
                        <h5><i class="fas fa-exclamation-triangle"></i> Karar Detayına Yönlendirme</h5>
                        <p class="mb-3">Karar metni otomatik olarak alınamadı. Manuel olarak görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                        <a href="{fallback_url}" target="_blank" class="btn btn-primary">
                            <i class="fas fa-external-link-alt"></i> {court_display_name} Karar Metnini Görüntüle
                        </a>
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="fas fa-info-circle"></i> Hata: {str(e)}
                            </small>
                        </div>
                    </div>
                    """,
                    'content_type': 'text',
                    'source_url': fallback_url,
                    'court_type': court_type,
                    'error_info': f'MCP Client hatası: {str(e)}'
                }
        except Exception as fallback_error:
            logger.error(f"Fallback web scraping de başarısız ({court_type}): {fallback_error}")
            return {
                'success': False,
                'error': f'Tüm yöntemler başarısız oldu: {str(e)}'
            }

# Uygulama kapatılırken HTTP session'ı kapatmak için
import atexit
def cleanup_resources():
    try:
        if hasattr(http_manager.session, 'close'):
            http_manager.session.close()
    except:
        pass

atexit.register(cleanup_resources) 