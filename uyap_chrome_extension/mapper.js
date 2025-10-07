// UYAP Veri Formatını Sistem Formatına Dönüştürme Modülü

/**
 * UYAP'tan gelen dosya verisini sisteme uygun formata dönüştürür
 * @param {Object} uyapData - UYAP'tan çekilen ham veri
 * @returns {Object} - Sisteme gönderilecek formatlanmış veri
 */
function mapUyapToSystem(uyapData) {
    console.log('UYAP verisi dönüştürülüyor:', uyapData);

    const mapped = {
        // Dosya bilgileri
        fileInfo: mapFileInfo(uyapData.caseInfo || {}),

        // Müvekkil bilgileri
        client: mapClient(uyapData.parties?.clients?.[0] || {}),
        additionalClients: mapAdditionalClients(uyapData.parties?.clients?.slice(1) || []),

        // Karşı taraf bilgileri
        opponent: mapOpponent(uyapData.parties?.opponents?.[0] || {}),
        additionalOpponents: mapAdditionalOpponents(uyapData.parties?.opponents?.slice(1) || []),

        // Vekil bilgileri
        lawyer: mapLawyer(uyapData.lawyers || []),

        // Belgeler
        documents: mapDocuments(uyapData.documents || []),

        // Duruşmalar
        hearings: mapHearings(uyapData.hearings || [])
    };

    console.log('Dönüştürülen veri:', mapped);
    return mapped;
}

/**
 * Dosya bilgilerini dönüştür
 */
function mapFileInfo(caseInfo) {
    // Dosya türünü eşleştir
    const fileType = CONFIG.COURT_TYPE_MAPPING[caseInfo.fileType] || 'hukuk';

    return {
        'file-type': fileType,
        'city': caseInfo.city || '',
        'courthouse': caseInfo.courthouse || '',
        'department': caseInfo.department || caseInfo.courthouse || '',
        'year': caseInfo.year || new Date().getFullYear(),
        'case-number': caseInfo.caseNumber || '',
        'open-date': caseInfo.openDate || formatDateToISO(new Date()),
        'status': mapStatus(caseInfo.status || 'Açık')
    };
}

/**
 * Ana müvekkil bilgilerini dönüştür
 */
function mapClient(client) {
    if (!client || !client.name) return {};

    return {
        'client-entity-type': client.entityType || 'person',
        'client-name': client.name || '',
        'client-capacity': client.capacity || '',
        'client-id': client.identityNumber || '',
        'client-phone': cleanPhoneNumber(client.phone || ''),
        'client-address': client.address || ''
    };
}

/**
 * Ek müvekkilleri dönüştür
 */
function mapAdditionalClients(clients) {
    if (!clients || clients.length === 0) return [];

    return clients.map(client => ({
        id: Date.now() + Math.random(),
        entity_type: client.entityType || 'person',
        name: client.name || '',
        capacity: client.capacity || '',
        identity_number: client.identityNumber || '',
        phone: cleanPhoneNumber(client.phone || ''),
        address: client.address || ''
    }));
}

/**
 * Ana karşı taraf bilgilerini dönüştür
 */
function mapOpponent(opponent) {
    if (!opponent || !opponent.name) return {};

    return {
        'opponent-entity-type': opponent.entityType || 'person',
        'opponent-name': opponent.name || '',
        'opponent-capacity': opponent.capacity || '',
        'opponent-id': opponent.identityNumber || '',
        'opponent-phone': cleanPhoneNumber(opponent.phone || ''),
        'opponent-address': opponent.address || ''
    };
}

/**
 * Ek karşı tarafları dönüştür
 */
function mapAdditionalOpponents(opponents) {
    if (!opponents || opponents.length === 0) return [];

    return opponents.map(opponent => ({
        id: Date.now() + Math.random(),
        entity_type: opponent.entityType || 'person',
        name: opponent.name || '',
        capacity: opponent.capacity || '',
        identity_number: opponent.identityNumber || '',
        phone: cleanPhoneNumber(opponent.phone || ''),
        address: opponent.address || ''
    }));
}

/**
 * Vekil bilgilerini dönüştür (sadece karşı taraf vekili)
 */
function mapLawyer(lawyers) {
    if (!lawyers || lawyers.length === 0) return {};

    // Karşı taraf vekilini bul
    const opponentLawyer = lawyers.find(l => l.isOpponent) || lawyers[0];

    if (!opponentLawyer) return {};

    return {
        'opponent-lawyer': opponentLawyer.name || '',
        'opponent-lawyer-bar': opponentLawyer.bar || '',
        'opponent-lawyer-bar-number': opponentLawyer.barNumber || '',
        'opponent-lawyer-phone': cleanPhoneNumber(opponentLawyer.phone || ''),
        'opponent-lawyer-address': opponentLawyer.address || ''
    };
}

/**
 * Belgeleri dönüştür
 */
function mapDocuments(documents) {
    if (!documents || documents.length === 0) return [];

    return documents.map(doc => ({
        documentType: CONFIG.DOCUMENT_TYPE_MAPPING[doc.documentType] || doc.documentType || 'Diğer Belgeler',
        fileName: doc.fileName || 'belge.pdf',
        uploadDate: doc.uploadDate || formatDateToISO(new Date()),
        downloadUrl: doc.downloadUrl || null,
        documentId: doc.documentId || null
    }));
}

/**
 * Duruşmaları dönüştür
 */
function mapHearings(hearings) {
    if (!hearings || hearings.length === 0) return [];

    return hearings.map(hearing => ({
        date: hearing.date || '',
        time: hearing.time || '',
        type: hearing.type || 'durusma',
        status: hearing.status || ''
    }));
}

/**
 * Dosya durumunu eşleştir
 */
function mapStatus(uyapStatus) {
    const statusMap = {
        'Açık': 'Aktif',
        'Kapalı': 'Kapalı',
        'Beklemede': 'Beklemede',
        'Sonuçlandı': 'Kapalı',
        'İnfaz': 'Kapalı'
    };

    return statusMap[uyapStatus] || 'Aktif';
}

/**
 * Telefon numarasını temizle (sadece rakamlar)
 */
function cleanPhoneNumber(phone) {
    if (!phone) return '';

    // Sadece rakamları al
    const cleaned = phone.replace(/\D/g, '');

    // Başındaki 0'ı kaldır (varsa)
    return cleaned.startsWith('0') ? cleaned.substring(1) : cleaned;
}

/**
 * Tarihi ISO formatına çevir (YYYY-MM-DD)
 */
function formatDateToISO(date) {
    if (!date) return '';

    if (typeof date === 'string') {
        // Eğer zaten ISO formatındaysa
        if (date.match(/^\d{4}-\d{2}-\d{2}$/)) {
            return date;
        }

        // DD.MM.YYYY formatından çevir
        const match = date.match(/(\d{2})\.(\d{2})\.(\d{4})/);
        if (match) {
            return `${match[3]}-${match[2]}-${match[1]}`;
        }

        // Date nesnesine çevir
        date = new Date(date);
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
}

/**
 * Form data olarak hazırla (Flask'a gönderim için)
 */
function prepareFormData(mappedData) {
    const formData = new FormData();

    // Dosya bilgileri
    Object.entries(mappedData.fileInfo).forEach(([key, value]) => {
        formData.append(key, value);
    });

    // Müvekkil bilgileri
    Object.entries(mappedData.client).forEach(([key, value]) => {
        formData.append(key, value);
    });

    // Ek müvekkiller (JSON)
    if (mappedData.additionalClients.length > 0) {
        formData.append('additional_clients_json', JSON.stringify(mappedData.additionalClients));
    }

    // Karşı taraf bilgileri
    Object.entries(mappedData.opponent).forEach(([key, value]) => {
        formData.append(key, value);
    });

    // Ek karşı taraflar (JSON)
    if (mappedData.additionalOpponents.length > 0) {
        formData.append('additional_opponents_json', JSON.stringify(mappedData.additionalOpponents));
    }

    // Vekil bilgileri
    Object.entries(mappedData.lawyer).forEach(([key, value]) => {
        formData.append(key, value);
    });

    return formData;
}

/**
 * JSON olarak hazırla (modern API için)
 */
function prepareJSON(mappedData) {
    return {
        ...mappedData.fileInfo,
        ...mappedData.client,
        ...mappedData.opponent,
        ...mappedData.lawyer,
        additional_clients_json: mappedData.additionalClients.length > 0 ?
            JSON.stringify(mappedData.additionalClients) : '',
        additional_opponents_json: mappedData.additionalOpponents.length > 0 ?
            JSON.stringify(mappedData.additionalOpponents) : '',
        documents: mappedData.documents,
        hearings: mappedData.hearings
    };
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        mapUyapToSystem,
        prepareFormData,
        prepareJSON
    };
}
