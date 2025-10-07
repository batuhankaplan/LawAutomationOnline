// UYAP Content Script - DOM'dan veri çekme v2.1.0 (major fixes)
console.log('🔧 UYAP Extension v2.1.0 - Vekil Bazlı Müvekkil Seçimi + Çoklu Dosya');

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

            // Detay linkini bul - önce href içinde "detay" olanı, sonra satırdaki herhangi bir linki, en son onclick olan elementi ara
            let detailUrl = null;
            const detailLink = row.querySelector('a[href*="detay"]');
            const anyLink = row.querySelector('a[href]');
            const clickableElement = row.querySelector('[onclick]');

            if (detailLink) {
                detailUrl = detailLink.href;
            } else if (anyLink) {
                detailUrl = anyLink.href;
            } else if (clickableElement) {
                // onclick'ten URL çıkarmaya çalış
                const onclick = clickableElement.getAttribute('onclick');
                const urlMatch = onclick.match(/['"]([^'"]*)['"]/);
                if (urlMatch) detailUrl = urlMatch[1];
            }

            const caseData = {
                rowId: row.dataset.id || Math.random().toString(36),
                birim: cellTexts[0] || '',
                dosyaNo: cellTexts[1] || '',
                dosyaTuru: cellTexts[2] || '',
                dosyaDurumu: cellTexts[3] || 'Açık',
                acilisTarihi: cellTexts[4] || '',
                goruntule: cellTexts[5] || '',
                selected: checkbox ? checkbox.checked : false,
                detailUrl: detailUrl,
                rawCells: cellTexts
            };

            cases.push(caseData);
        });
    });

    return cases;
}

// Dosya detaylarını sayfadan çekme (detay sayfasında)
async function extractCaseDetails() {
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

        // Taraf bilgilerini çek (async)
        details.parties = await extractParties();

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

    // Sayfa başlığından mahkeme ve esas no bilgilerini çek
    // Örnek: "2025/88 Bakırköy 8. İş Mahkemesi–Hukuk Dava Dosyası"
    const pageTitle = document.querySelector('h1, .page-title, [class*="title"]')?.textContent?.trim() || document.title;
    console.log('📄 Sayfa başlığı:', pageTitle);

    // Esas No ve Mahkeme adını parse et
    const titleMatch = pageTitle.match(/(\d{4})\/(\d+)\s+(.+?)(?:–|—|-|$)/);
    if (titleMatch) {
        info.year = titleMatch[1];
        info.caseNumber = titleMatch[2];
        info.courthouse = titleMatch[3].trim();
        console.log('✅ Başlıktan çıkarılan: Yıl=' + info.year + ', Esas=' + info.caseNumber + ', Mahkeme=' + info.courthouse);

        // Şehir ve adliye bilgisini mahkeme adından çıkar
        const cityInfo = extractCityFromCourthouse(info.courthouse);
        info.city = cityInfo.city;
        info.adliye = cityInfo.adliye;
    } else {
        // Fallback: Label-value çiftlerinden çek
        const esasNo = findLabelValue('Esas No', 'Dosya No', 'Esas Numarası', 'ESAS NO');
        if (esasNo) {
            const match = esasNo.match(/(\d{4})\/(\d+)/);
            if (match) {
                info.year = match[1];
                info.caseNumber = match[2];
            }
        }

        const mahkeme = findLabelValue('Mahkeme', 'Birim', 'Yargı Birimi');
        if (mahkeme) info.courthouse = mahkeme;
    }

    // Yargı türü
    const yargiTuru = findLabelValue('Yargı Türü', 'Yargı Birimi');
    if (yargiTuru) info.fileType = yargiTuru;

    // Açılış Tarihi
    const acilisTarihi = findLabelValue('Açılış Tarihi', 'Dava Açılış Tarihi', 'AÇILIŞ TARİHİ');
    if (acilisTarihi) info.openDate = parseUyapDate(acilisTarihi);

    // Dosya Durumu
    const durum = findLabelValue('Durum', 'Dosya Durumu', 'DURUM');
    if (durum) info.status = durum;

    // Sonraki Duruşma
    const durusmaTarihi = findLabelValue('Sonraki Duruşma', 'Duruşma Tarihi', 'SONRAKI DURUŞMA');
    if (durusmaTarihi) info.nextHearing = parseUyapDate(durusmaTarihi);

    console.log('📋 extractBasicCaseInfo sonuç:', info);
    return info;
}

// Tarafları çıkar (Müvekkil ve Karşı Taraf)
async function extractParties() {
    const parties = {
        clients: [],
        opponents: []
    };

    console.log('🔍 extractParties çağrıldı');

    // Önce "Taraf Bilgileri" sekmesine tıkla (varsa)
    await clickTabIfNeeded('Taraf');

    // Tablonun yüklenmesi için bekle
    await sleep(1500);

    // Tüm tabloları tara ve "Rol, Tipi, Adı, Vekil" başlıklı tabloyu bul
    const allTables = document.querySelectorAll('table');
    console.log(`📊 ${allTables.length} tablo taranıyor...`);

    let partyTable = null;
    let partyTableIndex = -1;

    for (let i = 0; i < allTables.length; i++) {
        const table = allTables[i];
        const headerCells = Array.from(table.querySelectorAll('th, tr:first-child td')).map(cell => cell.textContent.trim());

        // "Rol", "Tipi", "Adı" içeren tabloyu bul
        if (headerCells.some(h => h === 'Rol') && headerCells.some(h => h === 'Tipi' || h === 'Adı')) {
            console.log(`✅ Taraf tablosu bulundu (Tablo ${i}), başlıklar:`, headerCells);
            partyTableIndex = i;
            partyTable = allTables[i + 1]; // Bir sonraki tablo veri tablosu
            break;
        }
    }

    if (!partyTable) {
        console.warn('⚠️ Taraf tablosu bulunamadı!');
        return parties;
    }

    // Veri tablosunu parse et
    console.log('📋 Taraf verileri çekiliyor...');
    const rows = partyTable.querySelectorAll('tr');

    rows.forEach((row, index) => {
        const cells = Array.from(row.querySelectorAll('td')).map(cell => cell.textContent.trim());

        if (cells.length < 3 || !cells[0] || !cells[2]) {
            return; // Boş satır
        }

        const rol = cells[0]; // Davacı/Davalı
        const tipi = cells[1]; // Kişi/Kurum
        const adi = cells[2]; // İsim
        const vekil = cells[3] || ''; // Vekil

        console.log(`Satır ${index}: Rol=${rol}, Tipi=${tipi}, Adı=${adi}, Vekil=${vekil}`);

        const party = {
            name: adi,
            entityType: tipi.toLowerCase().includes('kurum') ? 'company' : 'person',
            capacity: rol,
            lawyer: vekil.replace(/[\[\]]/g, ''), // Köşeli parantezleri kaldır
            identityNumber: '',
            phone: '',
            address: ''
        };

        // Davacı = Client, Davalı = Opponent
        if (rol.toLowerCase().includes('davacı')) {
            parties.clients.push(party);
            console.log('👤 Davacı (Client) eklendi:', party);
        } else if (rol.toLowerCase().includes('davalı')) {
            parties.opponents.push(party);
            console.log('⚖️ Davalı (Opponent) eklendi:', party);
        }
    });

    console.log('📋 Final parties:', parties);
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
        // 1. Label elementleri ara (en güvenilir)
        const labelElements = document.querySelectorAll('label, .label, dt, th, div[class*="label"], span[class*="label"]');
        for (const elem of labelElements) {
            const labelText = elem.textContent.trim();
            if (labelText === label || labelText.includes(label + ':') || labelText.includes(label)) {
                // Değeri bul (sonraki element, input, span vs)
                let value = elem.nextElementSibling?.textContent?.trim();
                if (!value || value.length > 200) {
                    value = elem.parentElement?.querySelector('input, select, .value, dd, td')?.value;
                }
                if (!value || value.length > 200) {
                    value = elem.parentElement?.querySelector('.value, dd, td')?.textContent?.trim();
                }

                // Değer makul uzunlukta mı? (200 karakterden fazla ise muhtemelen tüm sayfayı çekmiştir)
                if (value && value.length < 200) {
                    return value;
                }
            }
        }

        // 2. Tablo satırlarını ara (tr > td yapısı)
        const tableRows = document.querySelectorAll('tr');
        for (const row of tableRows) {
            const cells = row.querySelectorAll('td, th');
            if (cells.length >= 2) {
                const cellLabel = cells[0].textContent.trim();
                if (cellLabel === label || cellLabel.includes(label)) {
                    const value = cells[1].textContent.trim();
                    if (value && value.length < 200) {
                        return value;
                    }
                }
            }
        }
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
        // Async fonksiyon, Promise ile handle et
        extractCaseDetails().then(details => {
            sendResponse({ success: true, data: details });
        }).catch(error => {
            console.error('getCaseDetails error:', error);
            sendResponse({ success: false, error: error.message });
        });
        return true; // Async response için gerekli
    }
    else if (request.action === 'checkPageType') {
        const isDetailPage = isUyapCaseDetailPage();
        sendResponse({ success: true, isDetailPage: isDetailPage });
    }
    else if (request.action === 'clickDetailButton') {
        const rowId = request.rowId;
        const dosyaNo = request.dosyaNo;
        console.log('🖱️ Dosya görüntüle butonuna tıklanıyor, dosyaNo:', dosyaNo, 'rowId:', rowId);

        // Tüm satırları ve butonları bul
        const rows = document.querySelectorAll('table tbody tr.dx-data-row, table tbody tr');
        let found = false;

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const cells = row.querySelectorAll('td');

            // Dosya numarasını kontrol et (genelde 2. sütun)
            const currentDosyaNo = cells[1]?.textContent.trim();

            if (currentDosyaNo === dosyaNo) {
                // Bu satırdaki butonu bul (son sütunda veya içinde)
                const detailBtn = row.querySelector('button[id*="goruntule"], button[title*="Görüntüle"], a[href*="detay"], #dosya-goruntule');
                if (detailBtn) {
                    console.log(`✅ ${dosyaNo} için buton bulundu (satır ${i}), tıklanıyor...`);
                    detailBtn.click();
                    found = true;
                    sendResponse({ success: true, message: 'Buton tıklandı' });
                    return;
                }
            }
        }

        if (!found) {
            console.error('❌ Dosya bulunamadı:', dosyaNo);
            sendResponse({ success: false, message: `Dosya ${dosyaNo} için buton bulunamadı` });
        }
    }
    else if (request.action === 'goBack') {
        console.log('🔙 Geri gidiliyor...');
        window.history.back();
        sendResponse({ success: true, message: 'Geri gidildi' });
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

// Helper: Sleep fonksiyonu
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper: Mahkeme adından şehir ve adliye bilgisi çıkar
function extractCityFromCourthouse(courthouse) {
    if (!courthouse) return { city: '', adliye: '' };

    // İlçe adlarını içeren mahkeme isimlerinden şehir çıkar
    const istanbulDistricts = ['Bakırköy', 'Kadıköy', 'Beşiktaş', 'Beyoğlu', 'Üsküdar', 'Şişli', 'Fatih', 'Zeytinburnu', 'Esenler', 'Güngören', 'Bahçelievler', 'Bağcılar', 'Küçükçekmece', 'Avcılar', 'Esenyurt', 'Başakşehir', 'Beylikdüzü', 'Çatalca', 'Silivri', 'Kartal', 'Maltepe', 'Pendik', 'Tuzla', 'Sultanbeyli', 'Sancaktepe', 'Ümraniye', 'Ataşehir', 'Çekmeköy', 'Sultangazi', 'Arnavutköy', 'Eyüpsultan'];
    const ankaraDistricts = ['Çankaya', 'Keçiören', 'Yenimahalle', 'Mamak', 'Sincan', 'Altındağ', 'Etimesgut', 'Pursaklar', 'Gölbaşı'];
    const izmirDistricts = ['Konak', 'Bornova', 'Karşıyaka', 'Buca', 'Bayraklı', 'Çiğli', 'Gaziemir', 'Balçova', 'Narlıdere'];

    let city = '';
    let district = '';

    // İstanbul ilçelerini kontrol et
    for (const dist of istanbulDistricts) {
        if (courthouse.includes(dist)) {
            city = 'İstanbul';
            district = dist;
            break;
        }
    }

    // Ankara ilçelerini kontrol et
    if (!city) {
        for (const dist of ankaraDistricts) {
            if (courthouse.includes(dist)) {
                city = 'Ankara';
                district = dist;
                break;
            }
        }
    }

    // İzmir ilçelerini kontrol et
    if (!city) {
        for (const dist of izmirDistricts) {
            if (courthouse.includes(dist)) {
                city = 'İzmir';
                district = dist;
                break;
            }
        }
    }

    // Eğer ilçe bulunamadıysa, mahkeme adının başındaki kelimeyi şehir olarak al
    if (!city) {
        const firstWord = courthouse.split(' ')[0];
        city = firstWord;
        district = firstWord;
    }

    // Adliye adını oluştur
    const adliye = district ? `${district} Adliyesi` : '';

    return { city, adliye };
}

// Helper: Sekmeye/Tab'a tıklama (varsa)
async function clickTabIfNeeded(tabName) {
    console.log(`🔍 "${tabName}" sekmesi aranıyor...`);

    // Buton, link veya tab elementi ara
    const buttons = document.querySelectorAll('button, a, div[role="tab"], div[role="button"]');

    for (const btn of buttons) {
        const text = btn.textContent.trim();
        if (text.toLowerCase().includes(tabName.toLowerCase())) {
            console.log(`✅ "${tabName}" sekmesi bulundu, tıklanıyor...`);
            btn.click();
            await sleep(500); // Tıklama sonrası kısa bekle
            return true;
        }
    }

    console.log(`⚠️ "${tabName}" sekmesi bulunamadı, devam ediliyor...`);
    return false;
}
