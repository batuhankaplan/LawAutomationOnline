// UYAP Veri Formatını Sistem Formatına Dönüştürme Modülü

/**
 * UYAP'tan gelen dosya verisini sisteme uygun formata dönüştürür
 * @param {Object} uyapData - UYAP'tan çekilen ham veri
 * @returns {Object} - Sisteme gönderilecek formatlanmış veri
 */
function mapUyapToSystem(uyapData) {
    console.log('UYAP verisi dönüştürülüyor:', uyapData);

    // Bizim vekiller listesi (bu vekillerden biri varsa o taraf müvekkil)
    const ourLawyers = ['BATUHAN KAPLAN', 'MUSTAFA KAPLAN', 'PERİZE KAPLAN', 'SELVİ DERTLİ'];

    // Tarafları analiz et ve müvekkil/karşı taraf ata
    const parties = identifyClientAndOpponent(uyapData.parties || {}, ourLawyers);

    // Eğer caseInfo'da sonraki duruşma varsa hearings array'e ekle
    const hearings = uyapData.hearings || [];
    const caseInfo = uyapData.caseInfo || {};

    if (caseInfo.nextHearing) {
        hearings.push({
            date: caseInfo.nextHearing,
            time: caseInfo.hearingTime || '09:00',
            type: 'durusma',
            status: ''
        });
    }

    const mapped = {
        // Dosya bilgileri
        fileInfo: mapFileInfo(uyapData.caseInfo || {}),

        // Müvekkil bilgileri
        client: mapClient(parties.client || {}),
        additionalClients: mapAdditionalClients(parties.additionalClients || []),

        // Karşı taraf bilgileri
        opponent: mapOpponent(parties.opponent || {}, parties.opponentLawyers || []),
        additionalOpponents: mapAdditionalOpponents(parties.additionalOpponents || []),

        // Vekil bilgileri (YENİ FORMAT: taraf bazlı)
        lawyers: mapLawyers(
            parties.clientLawyers || [],
            parties.opponentLawyers || [],
            uyapData.parties?.opponents || []  // Ham opponent data'dan vekil bilgisi
        ),

        // Belgeler
        documents: mapDocuments(uyapData.documents || []),

        // Duruşmalar
        hearings: mapHearings(hearings)
    };

    console.log('Dönüştürülen veri:', mapped);
    return mapped;
}

/**
 * Mahkeme adından sadece mahkeme kısmını çıkar
 * Örnek: "Bakırköy 8. İş Mahkemesi" -> "8. İş Mahkemesi"
 */
function extractCourtName(fullCourtName) {
    if (!fullCourtName) return '';

    // İstanbul ilçeleri
    const districts = [
        'Bakırköy', 'Kadıköy', 'Beşiktaş', 'Şişli', 'Ümraniye', 'Kartal',
        'Maltepe', 'Pendik', 'Ataşehir', 'Üsküdar', 'Beyoğlu', 'Fatih',
        'Eyüpsultan', 'Güngören', 'Bahçelievler', 'Bağcılar', 'Esenler',
        'Zeytinburnu', 'Avcılar', 'Küçükçekmece', 'Büyükçekmece',
        // Ankara ilçeleri
        'Çankaya', 'Keçiören', 'Mamak', 'Yenimahalle', 'Sincan', 'Etimesgut',
        'Altındağ', 'Pursaklar', 'Gölbaşı',
        // İzmir ilçeleri
        'Konak', 'Bornova', 'Karşıyaka', 'Buca', 'Bayraklı', 'Gaziemir',
        // Diğer şehirler (ilçe değil doğrudan şehir adı)
        'Tekirdağ', 'Edirne', 'Kırklareli', 'Çanakkale', 'Balıkesir',
        'Bursa', 'Kocaeli', 'Sakarya', 'Antalya', 'Adana', 'Mersin'
    ];

    // İlçe adını kaldır
    let courtName = fullCourtName;
    for (const district of districts) {
        if (courtName.includes(district)) {
            courtName = courtName.replace(district, '').trim();
            break;
        }
    }

    return courtName;
}

/**
 * Dosya bilgilerini dönüştür
 */
function mapFileInfo(caseInfo) {
    // Dosya türünü eşleştir
    const fileType = CONFIG.COURT_TYPE_MAPPING[caseInfo.fileType] || 'hukuk';

    // Açılış tarihini al ve formatla
    let openDate = caseInfo.openDate || caseInfo.acilisTarihi;
    if (openDate) {
        // Eğer DD.MM.YYYY HH:MM formatındaysa tarihi ayır
        const dateMatch = openDate.match(/(\d{2})\.(\d{2})\.(\d{4})/);
        if (dateMatch) {
            openDate = formatDateToISO(`${dateMatch[1]}.${dateMatch[2]}.${dateMatch[3]}`);
        } else {
            openDate = formatDateToISO(openDate);
        }
    } else {
        console.warn('⚠️ Açılış tarihi bulunamadı, güncel tarih kullanılıyor');
        openDate = formatDateToISO(new Date());
    }

    return {
        'file-type': fileType,
        'city': caseInfo.city || '',
        'courthouse': caseInfo.adliye || '',  // Backend'de courthouse = ADLİYE alanı
        'department': extractCourtName(caseInfo.courthouse) || '',  // Sadece mahkeme kısmı
        'year': caseInfo.year || new Date().getFullYear(),
        'case-number': caseInfo.caseNumber || '',
        'open-date': openDate,
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
        'client-name': capitalizeName(client.name) || '',
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
        name: capitalizeName(client.name) || '',
        capacity: client.capacity || '',
        identity_number: client.identityNumber || '',
        phone: cleanPhoneNumber(client.phone || ''),
        address: client.address || ''
    }));
}

/**
 * Ana karşı taraf bilgilerini dönüştür
 */
function mapOpponent(opponent, opponentLawyers) {
    if (!opponent || !opponent.name) return {};

    return {
        'opponent-entity-type': opponent.entityType || 'person',
        'opponent-name': capitalizeName(opponent.name) || '',
        'opponent-capacity': opponent.capacity || '',
        'opponent-id': opponent.identityNumber || '',
        'opponent-phone': cleanPhoneNumber(opponent.phone || ''),
        'opponent-address': opponent.address || ''
        // opponent-lawyer alanını kaldırdık, artık lawyers array'inde gönderilecek
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
        name: capitalizeName(opponent.name) || '',
        capacity: opponent.capacity || '',
        identity_number: opponent.identityNumber || '',
        phone: cleanPhoneNumber(opponent.phone || ''),
        address: opponent.address || ''
        // lawyer alanını kaldırdık, artık lawyers array'inde gönderilecek
    }));
}

/**
 * Vekil bilgilerini yeni formata dönüştür
 * Her vekil hangi tarafa ait olduğu bilgisi ile birlikte
 */
function mapLawyers(clientLawyers, opponentLawyers, additionalOpponents) {
    const lawyers = [];

    // Müvekkil vekilleri (client, index=0)
    if (clientLawyers && clientLawyers.length > 0) {
        clientLawyers.forEach(lawyerName => {
            if (lawyerName && lawyerName.trim() && lawyerName !== '-') {
                lawyers.push({
                    name: capitalizeName(lawyerName.trim()),
                    bar: '',
                    bar_number: '',
                    phone: '',
                    address: '',
                    party_type: 'client',
                    party_index: 0
                });
            }
        });
    }

    // Ana karşı taraf vekilleri (opponent, index=0)
    if (opponentLawyers && opponentLawyers.length > 0) {
        opponentLawyers.forEach(lawyerName => {
            if (lawyerName && lawyerName.trim() && lawyerName !== '-') {
                lawyers.push({
                    name: capitalizeName(lawyerName.trim()),
                    bar: '',
                    bar_number: '',
                    phone: '',
                    address: '',
                    party_type: 'opponent',
                    party_index: 0
                });
            }
        });
    }

    // Ek karşı tarafların vekilleri (opponent, index=1, 2, 3, ...)
    if (additionalOpponents && additionalOpponents.length > 0) {
        additionalOpponents.forEach((opponent, idx) => {
            if (opponent.lawyer && opponent.lawyer.trim() && opponent.lawyer !== '-') {
                // Virgülle ayrılmış birden fazla vekil olabilir
                const lawyerNames = opponent.lawyer.split(',').map(n => n.trim());
                lawyerNames.forEach(lawyerName => {
                    if (lawyerName && lawyerName !== '-') {
                        lawyers.push({
                            name: capitalizeName(lawyerName),
                            bar: '',
                            bar_number: '',
                            phone: '',
                            address: '',
                            party_type: 'opponent',
                            party_index: idx + 1  // +1 çünkü 0 ana karşı taraf
                        });
                    }
                });
            }
        });
    }

    return lawyers;
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
 * İsimleri proper case'e çevir: YENER SEVEN -> Yener Seven
 */
function capitalizeName(name) {
    if (!name) return name;

    // Türkçe karakterler için özel işlem
    const turkishUpper = {'İ': 'i', 'I': 'ı', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö', 'Ç': 'ç'};
    const turkishLower = {'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ', 'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç'};

    const words = name.split(/\s+/);
    const capitalizedWords = [];

    for (const word of words) {
        if (!word) continue;

        // İlk harfi büyük yap
        let firstChar = word[0];
        if (turkishUpper[firstChar]) {
            firstChar = turkishUpper[firstChar].toUpperCase();
        } else if (turkishLower[firstChar.toLowerCase()]) {
            firstChar = turkishLower[firstChar.toLowerCase()];
        } else {
            firstChar = firstChar.toUpperCase();
        }

        // Geri kalanı küçük yap
        const rest = word.slice(1).toLowerCase();
        capitalizedWords.push(firstChar + rest);
    }

    return capitalizedWords.join(' ');
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
        additional_clients_json: mappedData.additionalClients.length > 0 ?
            JSON.stringify(mappedData.additionalClients) : '',
        additional_opponents_json: mappedData.additionalOpponents.length > 0 ?
            JSON.stringify(mappedData.additionalOpponents) : '',
        // YENİ: Vekiller artık ayrı bir array olarak gönderiliyor
        lawyers: mappedData.lawyers,
        documents: mappedData.documents,
        hearings: mappedData.hearings
    };
}

/**
 * Tarafları analiz et ve vekil bazında müvekkil/karşı taraf belirle
 * @param {Object} parties - UYAP'tan gelen taraflar (clients, opponents)
 * @param {Array} ourLawyers - Bizim vekillerimizin isimleri
 * @returns {Object} - Düzenlenmiş taraf bilgileri
 */
function identifyClientAndOpponent(parties, ourLawyers) {
    const allParties = [
        ...(parties.clients || []).map(p => ({ ...p, originalRole: 'Davacı' })),
        ...(parties.opponents || []).map(p => ({ ...p, originalRole: 'Davalı' }))
    ];

    console.log('🔍 Taraflar analiz ediliyor:', allParties);
    console.log('👨‍⚖️ Bizim vekiller:', ourLawyers);

    let clientSide = [];
    let opponentSide = [];

    // Her tarafın vekilini kontrol et
    for (const party of allParties) {
        const lawyerNames = party.lawyer ? party.lawyer.toUpperCase().split(',').map(n => n.trim()) : [];
        const hasOurLawyer = lawyerNames.some(lawyerName =>
            ourLawyers.some(ourLawyer => lawyerName.includes(ourLawyer.toUpperCase()))
        );

        if (hasOurLawyer) {
            console.log(`✅ Müvekkil bulundu: ${party.name} (Vekil: ${party.lawyer})`);
            clientSide.push(party);
        } else {
            console.log(`⚖️ Karşı taraf: ${party.name} (Vekil: ${party.lawyer})`);
            opponentSide.push(party);
        }
    }

    // Eğer hiçbir tarafta bizim vekilimiz yoksa, rol bazlı atama yap
    if (clientSide.length === 0 && opponentSide.length > 0) {
        console.warn('⚠️ Bizim vekil bulunamadı, rol bazlı atama yapılıyor');

        // Hukuk dosyası: Davacı = Müvekkil
        // Ceza dosyası: Sanık = Müvekkil
        clientSide = allParties.filter(p =>
            p.capacity?.toLowerCase().includes('davacı') ||
            p.capacity?.toLowerCase().includes('sanık')
        );

        opponentSide = allParties.filter(p =>
            p.capacity?.toLowerCase().includes('davalı') ||
            p.capacity?.toLowerCase().includes('müşteki') ||
            p.capacity?.toLowerCase().includes('katılan')
        );
    }

    // Vekilleri ayır
    const clientLawyers = clientSide.length > 0 && clientSide[0].lawyer && clientSide[0].lawyer !== '-' ?
        clientSide[0].lawyer.split(',').map(l => l.trim().replace(/[\[\]]/g, '')).filter(l => l && l !== '-') : [];

    const opponentLawyers = opponentSide.length > 0 && opponentSide[0].lawyer && opponentSide[0].lawyer !== '-' ?
        opponentSide[0].lawyer.split(',').map(l => l.trim().replace(/[\[\]]/g, '')).filter(l => l && l !== '-') : [];

    return {
        client: clientSide[0] || null,
        additionalClients: clientSide.slice(1),
        opponent: opponentSide[0] || null,
        additionalOpponents: opponentSide.slice(1),
        clientLawyers: clientLawyers,
        opponentLawyers: opponentLawyers
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
