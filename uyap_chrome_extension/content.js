// UYAP Content Script - DOM'dan veri çekme
console.log('UYAP Dosya Aktarıcı Extension yüklendi');

// UYAP Dosya Sorgulama sayfasını algılama
function isUyapCaseListPage() {
    return window.location.href.includes('dosya') ||
           window.location.href.includes('sorgula') ||
           document.querySelector('table') !== null;
}

// UYAP Dosya Detay sayfasını algılama
function isUyapCaseDetailPage() {
    return window.location.href.includes('detay') ||
           document.querySelector('.case-detail') !== null ||
           document.querySelector('[id*="detail"]') !== null;
}

// Dosya listesini tablodan çekme
function extractCaseListFromTable() {
    const cases = [];
    const tables = document.querySelectorAll('table');

    tables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 3) return;

            // Hücre içeriklerini topla
            const cellTexts = Array.from(cells).map(cell => cell.textContent.trim());

            // Checkbox veya seçim butonu bul
            const checkbox = row.querySelector('input[type="checkbox"]');
            const detailButton = row.querySelector('button, a[href*="detay"]');

            const caseData = {
                rowId: row.dataset.id || Math.random().toString(36),
                birim: cellTexts[0] || '',
                dosyaNo: cellTexts[1] || '',
                dosyaTuru: cellTexts[2] || '',
                dosyaDurumu: cellTexts[3] || 'Açık',
                acilisTarihi: cellTexts[4] || '',
                goruntule: cellTexts[5] || '',
                selected: checkbox ? checkbox.checked : false,
                detailUrl: detailButton ? detailButton.href : null,
                rawCells: cellTexts
            };

            cases.push(caseData);
        });
    });

    return cases;
}

// Dosya detaylarını sayfadan çekme (detay sayfasında)
function extractCaseDetails() {
    const details = {
        caseInfo: {},
        parties: {
            clients: [],
            opponents: []
        },
        lawyers: [],
        documents: [],
        hearings: []
    };

    try {
        // Dosya bilgilerini çek
        details.caseInfo = extractBasicCaseInfo();

        // Taraf bilgilerini çek
        details.parties = extractParties();

        // Vekil bilgilerini çek
        details.lawyers = extractLawyers();

        // Belge listesini çek
        details.documents = extractDocuments();

        // Duruşma bilgilerini çek
        details.hearings = extractHearings();

    } catch (error) {
        console.error('Detay çıkarma hatası:', error);
    }

    return details;
}

// Temel dosya bilgilerini çıkar
function extractBasicCaseInfo() {
    const info = {};

    // Yargı türü
    const yargiTuru = findLabelValue('Yargı Türü', 'Yargı Birimi');
    if (yargiTuru) info.fileType = yargiTuru;

    // Mahkeme/Birim
    const mahkeme = findLabelValue('Mahkeme', 'Birim', 'Yargı Birimi');
    if (mahkeme) info.courthouse = mahkeme;

    // Esas No
    const esasNo = findLabelValue('Esas No', 'Dosya No', 'Esas Numarası');
    if (esasNo) {
        const match = esasNo.match(/(\d{4})\/(\d+)/);
        if (match) {
            info.year = match[1];
            info.caseNumber = match[2];
        }
    }

    // Açılış Tarihi
    const acilisTarihi = findLabelValue('Açılış Tarihi', 'Dava Açılış Tarihi');
    if (acilisTarihi) info.openDate = parseUyapDate(acilisTarihi);

    // Dosya Durumu
    const durum = findLabelValue('Durum', 'Dosya Durumu');
    if (durum) info.status = durum;

    // Şehir
    const sehir = findLabelValue('İl', 'Şehir');
    if (sehir) info.city = sehir;

    return info;
}

// Tarafları çıkar (Müvekkil ve Karşı Taraf)
function extractParties() {
    const parties = {
        clients: [],
        opponents: []
    };

    // Müvekkil tablosu/bölümü bul
    const clientSection = findSection(['Müvekkil', 'Müvekkillerimiz', 'Temsil Edilenler']);
    if (clientSection) {
        parties.clients = parsePartyTable(clientSection);
    }

    // Karşı taraf tablosu/bölümü bul
    const opponentSection = findSection(['Karşı Taraf', 'Karşı Taraflar', 'Diğer Taraflar']);
    if (opponentSection) {
        parties.opponents = parsePartyTable(opponentSection);
    }

    return parties;
}

// Taraf tablosunu parse et
function parsePartyTable(section) {
    const parties = [];
    const table = section.querySelector('table');

    if (table) {
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 2) return;

            const party = {
                name: cells[0]?.textContent.trim() || '',
                capacity: cells[1]?.textContent.trim() || '',
                identityNumber: cells[2]?.textContent.trim() || '',
                address: cells[3]?.textContent.trim() || '',
                phone: cells[4]?.textContent.trim() || '',
                entityType: detectEntityType(cells[0]?.textContent.trim())
            };

            if (party.name) parties.push(party);
        });
    } else {
        // Tablo yoksa liste formatında çek
        const items = section.querySelectorAll('li, .party-item');
        items.forEach(item => {
            const text = item.textContent.trim();
            const nameMatch = text.match(/^([^-:]+)/);
            const capacityMatch = text.match(/(?:Sıfat|Sıfatı):\s*([^\n]+)/i);

            if (nameMatch) {
                parties.push({
                    name: nameMatch[1].trim(),
                    capacity: capacityMatch ? capacityMatch[1].trim() : '',
                    entityType: detectEntityType(nameMatch[1].trim())
                });
            }
        });
    }

    return parties;
}

// Kişi/Kurum tespiti
function detectEntityType(name) {
    if (!name) return 'person';

    const companyKeywords = ['LTD', 'A.Ş', 'A.S', 'Limited', 'Anonim', 'Şirketi',
                             'Kooperatif', 'Dernek', 'Vakıf', 'Belediye', 'Müdürlüğü'];

    for (const keyword of companyKeywords) {
        if (name.toUpperCase().includes(keyword.toUpperCase())) {
            return 'company';
        }
    }

    return 'person';
}

// Vekilleri çıkar
function extractLawyers() {
    const lawyers = [];
    const lawyerSection = findSection(['Vekil', 'Vekillerimiz', 'Avukat']);

    if (lawyerSection) {
        const table = lawyerSection.querySelector('table');

        if (table) {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;

                const lawyer = {
                    name: cells[0]?.textContent.trim() || '',
                    bar: cells[1]?.textContent.trim() || '',
                    barNumber: cells[2]?.textContent.trim() || '',
                    phone: cells[3]?.textContent.trim() || '',
                    isOpponent: cells[4]?.textContent.trim().includes('Karşı') || false
                };

                if (lawyer.name) lawyers.push(lawyer);
            });
        }
    }

    return lawyers;
}

// Belgeleri çıkar
function extractDocuments() {
    const documents = [];
    const docSection = findSection(['Belge', 'Belgeler', 'Evrak']);

    if (docSection) {
        const table = docSection.querySelector('table');

        if (table) {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;

                const downloadLink = row.querySelector('a[href*="download"], button[onclick*="download"]');

                const doc = {
                    documentType: cells[0]?.textContent.trim() || '',
                    fileName: cells[1]?.textContent.trim() || '',
                    uploadDate: cells[2]?.textContent.trim() || '',
                    downloadUrl: downloadLink ? downloadLink.href || downloadLink.getAttribute('onclick') : null,
                    documentId: row.dataset.documentId || null
                };

                if (doc.fileName) documents.push(doc);
            });
        }
    }

    return documents;
}

// Duruşmaları çıkar
function extractHearings() {
    const hearings = [];
    const hearingSection = findSection(['Duruşma', 'Celses', 'Oturum']);

    if (hearingSection) {
        const table = hearingSection.querySelector('table');

        if (table) {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;

                const hearing = {
                    date: parseUyapDate(cells[0]?.textContent.trim()),
                    time: cells[1]?.textContent.trim() || '',
                    type: cells[2]?.textContent.trim() || 'durusma',
                    status: cells[3]?.textContent.trim() || ''
                };

                if (hearing.date) hearings.push(hearing);
            });
        }
    }

    return hearings;
}

// Yardımcı fonksiyonlar

// Etiket-değer çifti bul
function findLabelValue(...labels) {
    for (const label of labels) {
        // Label elementleri ara
        const labelElements = document.querySelectorAll('label, .label, dt, th');
        for (const elem of labelElements) {
            if (elem.textContent.includes(label)) {
                // Değeri bul (sonraki element, input, span vs)
                const value = elem.nextElementSibling?.textContent.trim() ||
                             elem.parentElement?.querySelector('input, select, .value, dd, td')?.value ||
                             elem.parentElement?.querySelector('.value, dd, td')?.textContent.trim();
                if (value) return value;
            }
        }

        // Tüm elementi tara (daha yavaş)
        const allText = document.body.textContent;
        const regex = new RegExp(`${label}\\s*:?\\s*([^\\n]+)`, 'i');
        const match = allText.match(regex);
        if (match) return match[1].trim();
    }

    return null;
}

// Bölüm bul (başlık altındaki içerik)
function findSection(titles) {
    for (const title of titles) {
        const headers = document.querySelectorAll('h1, h2, h3, h4, h5, .section-title, .panel-heading');
        for (const header of headers) {
            if (header.textContent.includes(title)) {
                return header.nextElementSibling || header.parentElement;
            }
        }
    }
    return null;
}

// UYAP tarih formatını parse et (DD.MM.YYYY -> YYYY-MM-DD)
function parseUyapDate(dateStr) {
    if (!dateStr) return null;

    const match = dateStr.match(/(\d{2})\.(\d{2})\.(\d{4})/);
    if (match) {
        return `${match[3]}-${match[2]}-${match[1]}`;
    }

    return dateStr;
}

// Extension'a mesaj dinleyicisi
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Content script mesaj aldı:', request);

    if (request.action === 'getCaseList') {
        const cases = extractCaseListFromTable();
        sendResponse({ success: true, data: cases });
    }
    else if (request.action === 'getCaseDetails') {
        const details = extractCaseDetails();
        sendResponse({ success: true, data: details });
    }
    else if (request.action === 'ping') {
        sendResponse({ success: true, message: 'Content script aktif' });
    }

    return true; // Async response için
});

// Sayfa yüklendiğinde buton ekle (opsiyonel)
window.addEventListener('load', () => {
    if (isUyapCaseListPage()) {
        addImportButton();
    }
});

// "Sisteme Aktar" butonu ekle
function addImportButton() {
    const button = document.createElement('button');
    button.textContent = '🔄 Dosyaları Sisteme Aktar';
    button.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        padding: 12px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    `;

    button.addEventListener('mouseenter', () => {
        button.style.transform = 'translateY(-2px)';
        button.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
    });

    button.addEventListener('mouseleave', () => {
        button.style.transform = 'translateY(0)';
        button.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
    });

    button.addEventListener('click', () => {
        chrome.runtime.sendMessage({ action: 'openPopup' });
    });

    document.body.appendChild(button);
}
