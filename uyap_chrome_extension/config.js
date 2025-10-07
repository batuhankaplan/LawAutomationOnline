// UYAP Chrome Extension Konfigürasyon Dosyası

const CONFIG = {
    // Backend API URL'leri
    API_BASE_URL: 'http://localhost:5000',
    API_ENDPOINTS: {
        IMPORT_CASE: '/api/import_from_uyap',
        UPLOAD_DOCUMENT: '/api/upload_uyap_document',
        CHECK_AUTH: '/api/check_auth'
    },

    // UYAP Yargı Türü Eşleştirmeleri
    COURT_TYPE_MAPPING: {
        'Hukuk': 'hukuk',
        'Ceza': 'ceza',
        'İcra': 'icra',
        'Savcılık': 'savcilik',
        'Arabuluculuk': 'ARABULUCULUK',
        'AİHM': 'AİHM',
        'AYM': 'AYM',
        'İdari Yargı': 'hukuk',
        'Satış Memurluğu': 'icra',
        'Tazminat Komisyonu Başkanlığı': 'hukuk',
        'Cbs': 'hukuk'
    },

    // Müvekkil/Karşı Taraf Sıfatları
    CAPACITIES: {
        hukuk: {
            client: ['Davacı', 'Davalı', 'Müdahil', 'İhtiyati Tedbir Talep Eden'],
            opponent: ['Davalı', 'Davacı', 'Müdahil', 'İhtiyati Tedbir Talepli']
        },
        ceza: {
            client: ['Sanık', 'Mağdur', 'Katılan', 'Şüpheli', 'Müşteki'],
            opponent: ['Mağdur', 'Sanık', 'Katılan', 'Müşteki', 'Şüpheli']
        },
        icra: {
            client: ['Borçlu', 'Alacaklı', 'İtiraz Eden', 'Şikayetçi'],
            opponent: ['Alacaklı', 'Borçlu', 'İtiraz Edilen', 'Şikayet Edilen']
        },
        savcilik: {
            client: ['Şüpheli', 'Mağdur', 'Müşteki', 'Şikayetçi'],
            opponent: ['Mağdur', 'Şüpheli', 'Müşteki', 'Sanık']
        }
    },

    // Belge Türü Eşleştirmeleri
    DOCUMENT_TYPE_MAPPING: {
        'Dilekçe': 'Dilekçe',
        'Dava Dilekçesi': 'Dava Dilekçesi',
        'Cevap Dilekçesi': 'Cevap Dilekçesi',
        'Karar': 'Karar',
        'Ara Karar': 'Ara Karar',
        'Nihai Karar': 'Nihai Karar',
        'Gerekçeli Karar': 'Gerekçeli Karar',
        'Tutanak': 'Duruşma Tutanağı',
        'Duruşma Tutanağı': 'Duruşma Tutanağı',
        'Tebligat': 'Tebligat',
        'İhbarname': 'İhbarname',
        'Ödeme Emri': 'Ödeme Emri',
        'İcra Emri': 'İcra Emri',
        'Bilirkişi Raporu': 'Bilirkişi Raporu',
        'Ek Belge': 'Ek Belge',
        'Diğer': 'Diğer Belgeler'
    },

    // UI Ayarları
    UI: {
        TOAST_DURATION: 3000,
        LOADING_DELAY: 500,
        MAX_RETRY_COUNT: 3,
        RETRY_DELAY: 1000
    },

    // Debug modu
    DEBUG: true
};

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
