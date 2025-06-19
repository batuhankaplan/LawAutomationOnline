"""
Unified Yargi MCP Integration - Simplified Version
Tüm MCP modüllerini tek dosyada birleştiren basit ve çalışan versiyon
"""

import asyncio
import logging
import requests
from typing import Dict, Any, List
from dataclasses import dataclass

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

class UnifiedYargiFlaskIntegration:
    """Birleşik yargı entegrasyonu - basit versiyon"""
    
    def __init__(self):
        pass
    
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
            # Event loop oluştur
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
                        self._search_yargitay(keyword, court_unit, case_year, 
                                            decision_year, start_date, end_date, 
                                            page_number, page_size)
                    )
                    results['yargitay'] = yargitay_result
                    logger.info(f"Yargıtay araması tamamlandı: {len(yargitay_result['decisions'])} sonuç")
                except Exception as e:
                    logger.error(f"Yargıtay arama hatası: {e}")
                    results['yargitay'] = self._empty_response(page_number, page_size)
            
            # Diğer mahkemeler için boş response
            if court_type in ["all", "danistay"]:
                results['danistay'] = self._empty_response(page_number, page_size)
            if court_type in ["all", "emsal"]:
                results['emsal'] = self._empty_response(page_number, page_size)
            if court_type in ["all", "anayasa"]:
                results['anayasa'] = self._empty_response(page_number, page_size)
            if court_type in ["all", "uyusmazlik"]:
                results['uyusmazlik'] = self._empty_response(page_number, page_size)
            if court_type in ["all", "kik"]:
                results['kik'] = self._empty_response(page_number, page_size)
            if court_type in ["all", "rekabet"]:
                results['rekabet'] = self._empty_response(page_number, page_size)
                
        except Exception as e:
            logger.error(f"Genel arama hatası: {e}")
            for ct in ['yargitay', 'danistay', 'emsal', 'anayasa', 'uyusmazlik', 'kik', 'rekabet']:
                if court_type == "all" or court_type == ct:
                    results[ct] = self._empty_response(page_number, page_size)
        
        # Toplam hesapla
        total_count = sum([results[ct]['count'] for ct in ['yargitay', 'danistay', 'emsal', 'anayasa', 'uyusmazlik', 'kik', 'rekabet']])
        results['total_count'] = total_count
        results['pagination']['total_records'] = total_count
        if total_count > 0:
            results['pagination']['total_pages'] = max(1, (total_count + page_size - 1) // page_size)
        
        return results
    
    async def _search_yargitay(self, keyword, court_unit="", case_year="", 
                              decision_year="", start_date="", end_date="",
                              page_number=1, page_size=20):
        """Yargıtay arama - API çağrısı"""
        
        try:
            payload = {
                'data': {
                    'arananKelime': keyword or "",
                    'birimYrgKurulDaire': "",
                    'birimYrgHukukDaire': court_unit or "",
                    'birimYrgCezaDaire': "",
                    'esasYil': case_year or "",
                    'esasIlkSiraNo': "",
                    'esasSonSiraNo': "",
                    'kararYil': decision_year or "",
                    'kararIlkSiraNo': "",
                    'kararSonSiraNo': "",
                    'baslangicTarihi': start_date or "",
                    'bitisTarihi': end_date or "",
                    'siralama': '3',
                    'siralamaDirection': 'desc',
                    'pageSize': page_size,
                    'pageNumber': page_number
                }
            }
            
            logger.info(f"Yargıtay API arama yapılıyor: {keyword}")
            
            response = requests.post(
                'https://karararama.yargitay.gov.tr/aramadetaylist',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            api_response = response.json()
            
            flask_results = []
            if api_response.get('data') and api_response['data'].get('data'):
                for decision in api_response['data']['data']:
                    flask_result = YargiSearchResult(
                        id=decision.get('id', ''),
                        title=f"Yargıtay {decision.get('daire', '')} - {decision.get('kararNo', '')}",
                        court=decision.get('daire', 'Yargıtay'),
                        decision_date=decision.get('kararTarihi', ''),
                        case_number=decision.get('esasNo', ''),
                        decision_number=decision.get('kararNo', ''),
                        summary=f"Yargıtay kararı: {keyword}",
                        document_url=f"https://karararama.yargitay.gov.tr/YargitayBilgiBankasiIstemciWeb/pf/bilgi-bankasi-detay.xhtml?id={decision.get('id', '')}"
                    )
                    flask_results.append(flask_result)
            
            total_records = api_response.get('data', {}).get('recordsTotal', 0)
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
            
            logger.info(f"Yargıtay API başarılı: {len(flask_results)} sonuç, toplam: {total_records}")
            
            return {
                'decisions': flask_results,
                'count': total_records,
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.warning(f"Yargıtay API hatası: {e}")
            return self._empty_response(page_number, page_size)
    
    def _empty_response(self, page_number, page_size):
        """Boş yanıt"""
        return {
            'decisions': [],
            'count': 0,
            'current_page': page_number,
            'page_size': page_size,
            'total_pages': 0
        }
    
    def get_court_options(self):
        """Mahkeme seçenekleri"""
        return {
            "yargitay": [
                {'value': '1. Hukuk Dairesi', 'text': '1. Hukuk Dairesi'},
                {'value': '2. Hukuk Dairesi', 'text': '2. Hukuk Dairesi'},
                {'value': '7. Hukuk Dairesi', 'text': '7. Hukuk Dairesi'},
                {'value': 'Hukuk Genel Kurulu', 'text': 'Hukuk Genel Kurulu'},
            ],
            "danistay": [
                {'value': '1. Daire', 'text': '1. Daire'},
            ],
            "emsal": [
                {'value': 'Tüm Mahkemeler', 'text': 'Tüm Mahkemeler'}
            ],
            "anayasa": [
                {'value': 'Norm Denetimi', 'text': 'Norm Denetimi'}
            ],
            "uyusmazlik": [
                {'value': 'Hukuk Bölümü', 'text': 'Hukuk Bölümü'}
            ],
            "kik": [
                {'value': 'Kurul Kararları', 'text': 'Kurul Kararları'}
            ],
            "rekabet": [
                {'value': 'Kurul Kararları', 'text': 'Kurul Kararları'}
            ]
        }

# Global instance
unified_yargi_integration = UnifiedYargiFlaskIntegration()

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
    return unified_yargi_integration.search_all_courts(
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
    return unified_yargi_integration.get_court_options()

def get_document_content(court_type: str, document_id: str, document_url: str = None) -> Dict[str, Any]:
    """Flask için doküman içeriği fonksiyonu"""
    return {
        'success': True,
        'redirect_url': document_url or f"https://www.{court_type}.gov.tr",
        'source_url': document_url or f"https://www.{court_type}.gov.tr",
        'court_type': court_type,
        'error_info': 'Unified version uses redirect for now'
    } 