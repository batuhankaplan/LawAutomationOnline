"""
Yargı MCP Flask Entegrasyonu
Gerçek yargi-mcp projesindeki tüm modülleri Flask uygulamasına entegre eder.
"""

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

# MCP modüllerini import et
from yargitay_mcp_module.client import YargitayOfficialApiClient
from yargitay_mcp_module.models import YargitayDetailedSearchRequest

from danistay_mcp_module.client import DanistayApiClient
from danistay_mcp_module.models import DanistayKeywordSearchRequest

from emsal_mcp_module.client import EmsalApiClient
from emsal_mcp_module.models import EmsalSearchRequest

from anayasa_mcp_module.client import AnayasaMahkemesiApiClient
from anayasa_mcp_module.models import AnayasaNormDenetimiSearchRequest

from uyusmazlik_mcp_module.client import UyusmazlikApiClient
from uyusmazlik_mcp_module.models import UyusmazlikSearchRequest, UyusmazlikBolumEnum

from kik_mcp_module.client import KikApiClient
from kik_mcp_module.models import KikSearchRequest, KikKararTipi

from rekabet_mcp_module.client import RekabetKurumuApiClient
from rekabet_mcp_module.models import RekabetKurumuSearchRequest

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
        """Yargıtay API'sinde arama yapar"""
        
        try:
            # Yargıtay arama parametrelerini hazırla
            search_request = YargitayDetailedSearchRequest(
                arananKelime=keyword,
                birimYrgKurulDaire=court_unit if court_unit and "Kurul" in court_unit else "",
                birimYrgHukukDaire=court_unit if court_unit and "Hukuk Dairesi" in court_unit else "",
                birimYrgCezaDaire=court_unit if court_unit and "Ceza Dairesi" in court_unit else "",
                esasYil=case_year,
                kararYil=decision_year,
                baslangicTarihi=start_date,
                bitisTarihi=end_date,
                pageNumber=page_number,
                pageSize=page_size,
                siralama="3",  # Karar tarihine göre
                siralamaDirection="desc"
            )
            
            logger.info(f"Yargıtay arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.yargitay_client.search_detailed_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.data and api_response.data.data:
                for decision in api_response.data.data:
                    flask_result = YargiSearchResult(
                        id=decision.id,
                        title=f"{decision.daire or 'Yargıtay'} - {decision.kararNo or 'Karar'}",
                        court=decision.daire or "Yargıtay",
                        decision_date=decision.kararTarihi or "",
                        case_number=decision.esasNo or "",
                        decision_number=decision.kararNo or "",
                        summary=f"Arama: {decision.arananKelime or keyword}"[:200],
                        document_url=str(decision.document_url) if hasattr(decision, 'document_url') and decision.document_url else ""
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.data.recordsTotal if api_response.data else 0
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Yargıtay arama hatası: {e}")
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
        """Danıştay API'sinde arama yapar"""
        
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
            
            logger.info(f"Danıştay arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.danistay_client.search_keyword_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.data and api_response.data.data:
                for decision in api_response.data.data:
                    # chamber özelliğini güvenli şekilde al
                    chamber = getattr(decision, 'chamber', None) or getattr(decision, 'daire', None) or "Danıştay"
                    
                    flask_result = YargiSearchResult(
                        id=decision.id,
                        title=f"Danıştay {chamber} - {decision.kararNo or ''}",
                        court=chamber,
                        decision_date=decision.kararTarihi or "",
                        case_number=decision.esasNo or "",
                        decision_number=decision.kararNo or "",
                        summary=f"Danıştay kararı: {keyword}"[:200],
                        document_url=str(decision.document_url) if hasattr(decision, 'document_url') and decision.document_url else ""
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.data.recordsTotal if api_response.data else 0
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Danıştay arama hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_emsal(self,
                           keyword: str,
                           page_number: int = 1,
                           page_size: int = 20) -> Dict[str, Any]:
        """Emsal API'sinde arama yapar"""
        
        try:
            # Emsal arama parametrelerini hazırla - doğru field adlarını kullan
            search_request = EmsalSearchRequest(
                keyword=keyword,  # Ana arama kelimesi
                case_year_esas=None,
                case_start_seq_esas=None,
                case_end_seq_esas=None,
                decision_year_karar=None,
                decision_start_seq_karar=None,
                decision_end_seq_karar=None,
                start_date=None,
                end_date=None,
                sort_criteria="1",
                sort_direction="desc",
                page_number=page_number,
                page_size=page_size
            )
            
            logger.info(f"Emsal arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.emsal_client.search_detailed_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.data and api_response.data.data:
                for decision in api_response.data.data:
                    # Mahkeme adını güvenli şekilde al
                    court_name = getattr(decision, 'daire', None) or "Emsal"
                    
                    flask_result = YargiSearchResult(
                        id=decision.id,
                        title=f"{court_name} - {decision.esasNo or 'N/A'}",
                        court=court_name,
                        decision_date=decision.kararTarihi or "",
                        case_number=decision.esasNo or "",
                        decision_number=decision.kararNo or "",
                        summary=f"Arama: {getattr(decision, 'arananKelime', keyword)}"[:200],
                        document_url=str(decision.document_url) if hasattr(decision, 'document_url') and decision.document_url else ""
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.data.recordsTotal if api_response.data else 0
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Emsal arama hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_anayasa(self,
                             keyword: str,
                             page_number: int = 1,
                             page_size: int = 20) -> Dict[str, Any]:
        """Anayasa Mahkemesi API'sinde arama yapar"""
        
        try:
            # Önce mevcut API'yi dene
            search_request = AnayasaNormDenetimiSearchRequest(
                keywords_all=[keyword] if keyword else [],
                keywords_any=[],
                keywords_exclude=[],
                page_to_fetch=page_number,
                results_per_page=page_size
            )
            
            logger.info(f"Anayasa Mahkemesi arama yapılıyor: {keyword}")
            
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
                            document_url=str(decision.document_url) if hasattr(decision, 'document_url') and decision.document_url else ""
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
                
                # API başarısız, alternatif web scraping dene
                logger.info("Anayasa Mahkemesi web scraping deneniyor...")
                
                # Farklı URL formatlarını dene
                possible_urls = [
                    f"https://www.anayasa.gov.tr/tr/kararlar/arama?q={keyword}",
                    f"https://kararlarbilgibankasi.anayasa.gov.tr/arama?kelime={keyword}",
                    f"https://anayasa.gov.tr/tr/kararlar/arama?arama={keyword}",
                    f"https://normkararlarbilgibankasi.anayasa.gov.tr/Ara?kelime={keyword}"
                ]
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                for url in possible_urls:
                    try:
                        logger.info(f"Anayasa Mahkemesi URL deneniyor: {url}")
                        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                        
                        if response.status_code == 200:
                            logger.info(f"Anayasa Mahkemesi başarılı URL: {url}")
                            
                            # HTML'den sonuçları çıkarmaya çalış
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Karar sonuçlarını bul
                            flask_results = []
                            
                            # Farklı HTML yapılarını dene
                            result_selectors = [
                                '.karar-item', '.decision-item', '.result-item',
                                '.karar', '.decision', '.result',
                                'tr[class*="karar"]', 'div[class*="karar"]',
                                'li[class*="result"]', 'div[class*="result"]'
                            ]
                            
                            for selector in result_selectors:
                                try:
                                    elements = soup.select(selector)
                                    if elements:
                                        logger.info(f"Anayasa Mahkemesi sonuç bulundu: {len(elements)} adet ({selector})")
                                        
                                        for i, element in enumerate(elements[:page_size]):
                                            # Basit sonuç oluştur
                                            title_elem = element.find(['h3', 'h4', 'h5', 'strong', 'b']) or element
                                            title = title_elem.get_text(strip=True)[:100] if title_elem else f"Anayasa Mahkemesi Kararı {i+1}"
                                            
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
                                                document_url=doc_url
                                            )
                                            flask_results.append(flask_result)
                                        
                                        break  # İlk başarılı selector'da dur
                                        
                                except Exception as e:
                                    continue
                            
                            if flask_results:
                                return {
                                    'decisions': flask_results,
                                    'count': len(flask_results),
                                    'current_page': page_number,
                                    'page_size': page_size,
                                    'total_pages': 1
                                }
                            
                    except Exception as url_error:
                        logger.warning(f"Anayasa Mahkemesi URL hatası ({url}): {url_error}")
                        continue
                
                # Hiçbir URL çalışmadı
                logger.warning("Anayasa Mahkemesi: Hiçbir URL çalışmadı")
                return self._empty_response(page_number, page_size)
            
        except Exception as e:
            logger.error(f"Anayasa Mahkemesi arama hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_uyusmazlik(self,
                                keyword: str,
                                page_number: int = 1,
                                page_size: int = 20) -> Dict[str, Any]:
        """Uyuşmazlık Mahkemesi API'sinde arama yapar"""
        
        try:
            # UyusmazlikBolumEnum'dan doğru değeri kullan
            from uyusmazlik_mcp_module.models import UyusmazlikBolumEnum
            
            # Uyuşmazlık Mahkemesi arama parametrelerini hazırla
            search_request = UyusmazlikSearchRequest(
                icerik=keyword,
                bolum=UyusmazlikBolumEnum.TUMU,  # Tüm bölümlerde ara
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
            
            logger.info(f"Uyuşmazlık Mahkemesi arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.uyusmazlik_client.search_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.decisions:
                for decision in api_response.decisions[:page_size]:  # Sayfalama için sınırla
                    # Model alanlarını doğru şekilde kullan
                    karar_sayisi = getattr(decision, 'karar_sayisi', None) or 'N/A'
                    esas_sayisi = getattr(decision, 'esas_sayisi', None) or 'N/A'
                    
                    flask_result = YargiSearchResult(
                        id=karar_sayisi,
                        title=f"Uyuşmazlık Mahkemesi - {karar_sayisi}",
                        court="Uyuşmazlık Mahkemesi",
                        decision_date="",  # Model'de karar tarihi alanı yok
                        case_number=esas_sayisi,
                        decision_number=karar_sayisi,
                        summary=f"Uyuşmazlık Mahkemesi kararı: {keyword}"[:200],
                        document_url=str(decision.document_url) if hasattr(decision, 'document_url') and decision.document_url else ""
                    )
                    flask_results.append(flask_result)
            
            total_records = getattr(api_response, 'total_records_found', len(flask_results)) or len(flask_results)
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Uyuşmazlık Mahkemesi arama hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_kik(self,
                         keyword: str,
                         page_number: int = 1,
                         page_size: int = 20) -> Dict[str, Any]:
        """KİK API'sinde arama yapar"""
        
        try:
            # KİK enum değerlerini kontrol et
            from kik_mcp_module.models import KikKararTipi
            
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
            
            logger.info(f"KİK arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.kik_client.search_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.decisions:
                for decision in api_response.decisions[:page_size]:  # Sayfalama için sınırla
                    # Model alanlarını doğru şekilde kullan
                    karar_no = getattr(decision, 'karar_no_str', None) or getattr(decision, 'kararNo', 'N/A')
                    karar_tarihi = getattr(decision, 'karar_tarihi_str', None) or getattr(decision, 'kararTarihi', '')
                    
                    flask_result = YargiSearchResult(
                        id=karar_no,
                        title=f"KİK - {karar_no}",
                        court="Kamu İhale Kurumu",
                        decision_date=karar_tarihi,
                        case_number="N/A",
                        decision_number=karar_no,
                        summary=f"KİK kararı: {keyword}"[:200],
                        document_url=f"kik:{decision.preview_event_target}" if hasattr(decision, 'preview_event_target') else ""
                    )
                    flask_results.append(flask_result)
            
            total_records = getattr(api_response, 'total_records', len(flask_results))
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"KİK arama hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    async def _search_rekabet(self,
                             keyword: str,
                             page_number: int = 1,
                             page_size: int = 20) -> Dict[str, Any]:
        """Rekabet Kurumu API'sinde arama yapar"""
        
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
            
            logger.info(f"Rekabet Kurumu arama yapılıyor: {keyword}")
            
            # API çağrısı yap
            api_response = await self.rekabet_client.search_decisions(search_request)
            
            # Sonuçları Flask formatına çevir
            flask_results = []
            if api_response.decisions:
                for decision in api_response.decisions[:page_size]:  # Sayfalama için sınırla
                    flask_result = YargiSearchResult(
                        id=decision.karar_id,
                        title=f"Rekabet - {decision.decision_number}",
                        court="Rekabet Kurumu",
                        decision_date=decision.decision_date or "",
                        case_number="N/A",
                        decision_number=decision.decision_number or "",
                        summary=f"Arama: {decision.decision_number}",
                        document_url=str(decision.decision_url) if decision.decision_url else ""
                    )
                    flask_results.append(flask_result)
            
            # total_records özelliğini güvenli şekilde al
            total_records = getattr(api_response, 'total_records', len(flask_results))
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Rekabet Kurumu arama hatası: {e}")
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
                                    (any(keyword in text.lower() for keyword in ['karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'esas', 'sonuç']) or
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
                    
                    # Metni temizle
                    cleaned_text = self._clean_decision_text(best_text)
                    
                    # Başarı kriterleri - daha esnek
                    if len(cleaned_text) > 150:  # Daha düşük minimum
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
                
                # Metni temizle
                cleaned_text = self._clean_decision_text(best_text)
                
                # Başarı kriterleri - daha esnek
                if len(cleaned_text) > 200:  # Minimum 200 karakter
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
        """UYAP Emsal kararının tam içeriğini çoklu yöntemle getirir."""
        
        # Farklı URL formatlarını dene
        url_formats = [
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/bilgi-bankasi-detay.xhtml?id={document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/detay.xhtml?id={document_id}",
            f"https://emsal.uyap.gov.tr/detay/{document_id}",
            f"https://www.uyap.gov.tr/emsal/detay/{document_id}",
            f"https://emsal.uyap.gov.tr/BilgiBankasiIstemciWeb/pf/karardetay.xhtml?id={document_id}"
        ]
        
        for attempt, source_url in enumerate(url_formats, 1):
            try:
                logger.info(f"Emsal karar metni deneme {attempt}/{len(url_formats)}: {source_url}")
                
                # HTTP isteği ile sayfayı çek
                response = self.http_manager.get_content(source_url, timeout=20)
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
                        'court_type': 'emsal'
                    }
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Gereksiz elementleri kaldır
                for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "input", "select"]):
                    element.decompose()
                
                # Çoklu selector deneme
                selectors_groups = [
                    # UYAP Emsal spesifik selectorlar
                    ["div.ui-panel-content", "div.ui-widget-content", "div.karar-metni", "div.karar-icerik"],
                    # Genel content selectorlar
                    ["div[id*='panel']", "div[class*='content']", "div[class*='karar']", "div[class*='detay']"],
                    # Tablo ve liste selectorlar
                    ["table.karar-tablosu", "div.karar-bilgileri", "div.icerik", "div.metin"],
                    # Fallback selectorlar
                    ["main", "article", "section", ".container", ".content"]
                ]
                
                best_text = ""
                best_source = ""
                
                for group_idx, selectors in enumerate(selectors_groups):
                    for selector in selectors:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text(separator='\n', strip=True)
                            # Emsal için özel kriterler
                            if (len(text) > len(best_text) and 
                                len(text) > 200 and
                                any(keyword in text.lower() for keyword in ['karar', 'hüküm', 'gerekçe', 'mahkeme', 'dava', 'esas', 'sonuç', 'emsal', 'uyap'])):
                                best_text = text
                                best_source = f"Group {group_idx+1}, Selector: {selector}"
                                logger.info(f"Deneme {attempt}: Daha iyi metin bulundu - {len(text)} karakter ({best_source})")
                
                # Eğer spesifik selector bulamazsa, body'den al
                if len(best_text) < 500 and soup.body:
                    body_text = soup.body.get_text(separator='\n', strip=True)
                    # Sadece karar metni gibi görünen kısımları al
                    lines = body_text.split('\n')
                    filtered_lines = []
                    skip_keywords = ['menü', 'navigation', 'footer', 'header', 'cookie', 'javascript', 'login', 'giriş', 'çıkış', 'uyap', 'bilgi bankası']
                    
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
                
                # Metni temizle
                cleaned_text = self._clean_decision_text(best_text)
                
                # Başarı kriterleri - daha esnek
                if len(cleaned_text) > 200:  # Minimum 200 karakter
                    logger.info(f"Emsal metni başarıyla çekildi (Deneme {attempt}): {len(cleaned_text)} karakter - {best_source}")
                    return {
                        'success': True, 
                        'content': cleaned_text, 
                        'content_type': 'text', 
                        'source_url': source_url, 
                        'court_type': 'emsal',
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
            'court_type': 'emsal',
            'error_info': 'Tüm extraction yöntemleri başarısız oldu'
        }

    async def _get_anayasa_document_content(self, document_id: str) -> Dict[str, Any]:
        """Anayasa Mahkemesi kararının tam içeriğini getir"""
        try:
            # Anayasa Mahkemesi için URL yönlendirmesi
            source_url = f"https://normkararlarbilgibankasi.anayasa.gov.tr/Karar/Goster/{document_id}"
            
            return {
                'success': True,
                'content': f"""
                <div class="alert alert-info">
                    <h5><i class="fas fa-info-circle"></i> Karar Detayına Yönlendirme</h5>
                    <p>Kararın tam metnini görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                    <a href="{source_url}" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt"></i> Anayasa Mahkemesi Karar Metnini Görüntüle
                    </a>
                </div>
                """,
                'source_url': source_url,
                'court_type': 'anayasa'
            }
        except Exception as e:
            logger.error(f"Anayasa Mahkemesi doküman içeriği hatası: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _get_uyusmazlik_document_content(self, document_id: str) -> Dict[str, Any]:
        """Uyuşmazlık Mahkemesi kararının tam içeriğini getir"""
        try:
            # Uyuşmazlık Mahkemesi için URL yönlendirmesi
            source_url = f"https://kararlar.uyusmazlik.gov.tr/Karar/Detay/{document_id}"
            
            return {
                'success': True,
                'content': f"""
                <div class="alert alert-info">
                    <h5><i class="fas fa-info-circle"></i> Karar Detayına Yönlendirme</h5>
                    <p>Kararın tam metnini görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                    <a href="{source_url}" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt"></i> Uyuşmazlık Mahkemesi Karar Metnini Görüntüle
                    </a>
                </div>
                """,
                'source_url': source_url,
                'court_type': 'uyusmazlik'
            }
        except Exception as e:
            logger.error(f"Uyuşmazlık Mahkemesi doküman içeriği hatası: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _get_kik_document_content(self, document_id: str) -> Dict[str, Any]:
        """KİK kararının tam içeriğini getir"""
        try:
            # KİK için özel format kontrolü
            if document_id.startswith("kik:"):
                event_target = document_id[4:]  # "kik:" kısmını kaldır
                source_url = f"https://www.kik.gov.tr/Kararlar/Detay/{event_target}"
            else:
                source_url = f"https://www.kik.gov.tr/Kararlar/Detay/{document_id}"
                
            return {
                'success': True,
                'content': f"""
                <div class="alert alert-info">
                    <h5><i class="fas fa-info-circle"></i> Karar Detayına Yönlendirme</h5>
                    <p>Kararın tam metnini görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                    <a href="{source_url}" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt"></i> KİK Karar Metnini Görüntüle
                    </a>
                </div>
                """,
                'source_url': source_url,
                'court_type': 'kik'
            }
        except Exception as e:
            logger.error(f"KİK doküman içeriği hatası: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _get_rekabet_document_content(self, document_url: str) -> Dict[str, Any]:
        """Rekabet Kurumu kararının tam içeriğini getir"""
        try:
            # Rekabet Kurumu için doğrudan URL kullan
            source_url = document_url if document_url else "https://www.rekabet.gov.tr/tr/Kararlar"
            
            return {
                'success': True,
                'content': f"""
                <div class="alert alert-info">
                    <h5><i class="fas fa-info-circle"></i> Karar Detayına Yönlendirme</h5>
                    <p>Kararın tam metnini görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
                    <a href="{source_url}" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt"></i> Rekabet Kurumu Karar Metnini Görüntüle
                    </a>
                </div>
                """,
                'source_url': source_url,
                'court_type': 'rekabet'
            }
        except Exception as e:
            logger.error(f"Rekabet Kurumu doküman içeriği hatası: {e}")
            return {
                'success': False,
                'error': str(e)
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
            # Yargıtay için yeni client oluştur (event loop sorunu nedeniyle)
            from yargitay_mcp_module.client import YargitayOfficialApiClient
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
            # Danıştay için yeni client oluştur
            from danistay_mcp_module.client import DanistayApiClient
            client = DanistayApiClient()
            
            try:
                result = loop.run_until_complete(
                    client.get_decision_document_as_markdown(document_id)
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
            # Emsal için yeni client oluştur
            from emsal_mcp_module.client import EmsalApiClient
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
            # Anayasa Mahkemesi için yeni client oluştur
            from anayasa_mcp_module.client import AnayasaMahkemesiApiClient
            client = AnayasaMahkemesiApiClient()
            
            try:
                # document_url'den path çıkar
                document_path = document_url
                if document_url and document_url.startswith('http'):
                    # URL'den path kısmını çıkar
                    from urllib.parse import urlparse
                    parsed = urlparse(document_url)
                    document_path = parsed.path
                
                result = loop.run_until_complete(
                    client.get_norm_denetimi_document_as_markdown(
                        document_url=document_path or document_id,
                        page_number=1
                    )
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
            # Uyuşmazlık Mahkemesi için yeni client oluştur
            from uyusmazlik_mcp_module.client import UyusmazlikApiClient
            client = UyusmazlikApiClient()
            
            try:
                if not document_url:
                    # URL yoksa fallback
                    return loop.run_until_complete(
                        yargi_integration._get_uyusmazlik_document_content(document_id)
                    )
                
                result = loop.run_until_complete(
                    client.get_document_as_markdown_from_url(document_url)
                )
                
                if result and result.markdown_content:
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
                    logger.warning("Uyuşmazlık Mahkemesi markdown içeriği boş")
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
            # KİK için yeni client oluştur
            from kik_mcp_module.client import KikApiClient
            client = KikApiClient()
            
            try:
                result = loop.run_until_complete(
                    client.get_document_as_markdown(
                        karar_id=document_id,
                        page_number=1
                    )
                )
                
                if result and result.markdown_content:
                    logger.info(f"KİK markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                    return {
                        'success': True,
                        'content': result.markdown_content,
                        'content_type': 'text',
                        'source_url': str(result.source_url) if result.source_url else '',
                        'court_type': 'kik',
                        'extraction_method': 'MCP Client API'
                    }
                else:
                    logger.warning("KİK markdown içeriği boş")
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
            # Rekabet Kurumu için yeni client oluştur
            from rekabet_mcp_module.client import RekabetKurumuApiClient
            client = RekabetKurumuApiClient()
            
            try:
                result = loop.run_until_complete(
                    client.get_document(
                        karar_id=document_id,
                        page_number=1
                    )
                )
                
                if result and result.markdown_content:
                    logger.info(f"Rekabet Kurumu markdown içeriği başarıyla alındı: {len(result.markdown_content)} karakter")
                    return {
                        'success': True,
                        'content': result.markdown_content,
                        'content_type': 'text',
                        'source_url': str(result.source_url) if result.source_url else '',
                        'court_type': 'rekabet',
                        'extraction_method': 'MCP Client API'
                    }
                else:
                    logger.warning("Rekabet Kurumu markdown içeriği boş")
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
            else:
                # Diğer mahkemeler için yönlendirme döndür
                return {
                    'success': True,
                    'redirect_url': document_url or f"https://www.{court_type}.gov.tr",
                    'source_url': document_url or f"https://www.{court_type}.gov.tr",
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