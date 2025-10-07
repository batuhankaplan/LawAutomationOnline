// Background Service Worker - API İletişimi ve State Yönetimi

console.log('UYAP Dosya Aktarıcı Background Service başlatıldı');

// Global state
let currentCases = [];
let importProgress = {};

// Chrome storage'dan ayarları yükle
async function loadSettings() {
    return new Promise((resolve) => {
        chrome.storage.sync.get(['apiUrl', 'autoSync'], (result) => {
            resolve({
                apiUrl: result.apiUrl || 'http://localhost:5000',
                autoSync: result.autoSync || false
            });
        });
    });
}

// Ayarları kaydet
async function saveSettings(settings) {
    return new Promise((resolve) => {
        chrome.storage.sync.set(settings, resolve);
    });
}

// Mesaj dinleyicisi
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Background mesaj aldı:', request);

    if (request.action === 'openPopup') {
        chrome.action.openPopup();
        sendResponse({ success: true });
    }
    else if (request.action === 'importCase') {
        handleImportCase(request.data).then(sendResponse);
        return true; // Async
    }
    else if (request.action === 'importMultipleCases') {
        handleImportMultipleCases(request.cases).then(sendResponse);
        return true; // Async
    }
    else if (request.action === 'downloadDocument') {
        handleDownloadDocument(request.url, request.filename).then(sendResponse);
        return true; // Async
    }
    else if (request.action === 'checkAuth') {
        checkBackendAuth().then(sendResponse);
        return true; // Async
    }
    else if (request.action === 'getProgress') {
        sendResponse({ progress: importProgress });
    }

    return true;
});

// Backend authentication kontrolü
async function checkBackendAuth() {
    try {
        const settings = await loadSettings();
        const response = await fetch(`${settings.apiUrl}/api/check_auth`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            return { success: true, authenticated: data.authenticated, user: data.user };
        }

        return { success: false, authenticated: false };
    } catch (error) {
        console.error('Auth check hatası:', error);
        return { success: false, error: error.message };
    }
}

// Tek dosya import
async function handleImportCase(caseData) {
    try {
        const settings = await loadSettings();

        // Import progress başlat
        const importId = Date.now().toString();
        importProgress[importId] = {
            status: 'başlatılıyor',
            progress: 0,
            currentStep: 'Dosya bilgileri gönderiliyor...'
        };

        // Backend'e gönder
        const response = await fetch(`${settings.apiUrl}/api/import_from_uyap`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(caseData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Import başarısız');
        }

        const result = await response.json();

        // Progress güncelle
        importProgress[importId] = {
            status: 'tamamlandı',
            progress: 100,
            currentStep: 'Dosya başarıyla eklendi',
            caseId: result.case_id
        };

        // Belgeleri yükle (varsa)
        if (caseData.documents && caseData.documents.length > 0) {
            await handleDocumentUploads(result.case_id, caseData.documents, importId);
        }

        return {
            success: true,
            case_id: result.case_id,
            message: 'Dosya başarıyla aktarıldı',
            importId
        };

    } catch (error) {
        console.error('Import hatası:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Çoklu dosya import
async function handleImportMultipleCases(cases) {
    const results = [];
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < cases.length; i++) {
        const caseData = cases[i];

        try {
            const result = await handleImportCase(caseData);

            if (result.success) {
                successCount++;
            } else {
                failCount++;
            }

            results.push({
                caseNo: caseData.caseInfo?.caseNumber,
                ...result
            });

            // Progress güncelle
            const progress = ((i + 1) / cases.length) * 100;
            chrome.runtime.sendMessage({
                action: 'updateBulkProgress',
                progress,
                current: i + 1,
                total: cases.length
            });

            // API'yi aşırı yüklememek için kısa bekleme
            await sleep(500);

        } catch (error) {
            failCount++;
            results.push({
                caseNo: caseData.caseInfo?.caseNumber,
                success: false,
                error: error.message
            });
        }
    }

    return {
        success: true,
        summary: {
            total: cases.length,
            success: successCount,
            failed: failCount
        },
        results
    };
}

// Belge indirme ve yükleme
async function handleDocumentUploads(caseId, documents, importId) {
    const settings = await loadSettings();
    let uploaded = 0;

    for (const doc of documents) {
        try {
            // İlerlemeyi güncelle
            importProgress[importId].currentStep = `Belge indiriliyor: ${doc.fileName}`;
            importProgress[importId].progress = 50 + (uploaded / documents.length) * 50;

            // Belgeyi indir
            const blob = await downloadDocumentAsBlob(doc.downloadUrl);

            if (!blob) {
                console.error('Belge indirilemedi:', doc.fileName);
                continue;
            }

            // FormData oluştur
            const formData = new FormData();
            formData.append('document', blob, doc.fileName);
            formData.append('document_type', doc.documentType);
            formData.append('document_date', doc.uploadDate);

            // Backend'e yükle
            const response = await fetch(
                `${settings.apiUrl}/api/upload_uyap_document/${caseId}`,
                {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                }
            );

            if (response.ok) {
                uploaded++;
            }

        } catch (error) {
            console.error('Belge yükleme hatası:', error);
        }
    }

    return { uploaded, total: documents.length };
}

// Belgeyi blob olarak indir
async function handleDownloadDocument(url, filename) {
    try {
        const blob = await downloadDocumentAsBlob(url);

        if (blob) {
            return {
                success: true,
                blob,
                filename
            };
        }

        return { success: false, error: 'İndirme başarısız' };

    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Fetch ile blob indirme
async function downloadDocumentAsBlob(url) {
    try {
        // UYAP URL'i ise cookie'li fetch
        if (url.includes('uyap.gov.tr')) {
            const response = await fetch(url, {
                credentials: 'include'
            });

            if (response.ok) {
                return await response.blob();
            }
        }

        return null;
    } catch (error) {
        console.error('Blob indirme hatası:', error);
        return null;
    }
}

// Yardımcı fonksiyonlar
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Extension yüklendiğinde
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('UYAP Dosya Aktarıcı ilk kez yüklendi');

        // Varsayılan ayarları kaydet
        saveSettings({
            apiUrl: 'http://localhost:5000',
            autoSync: false
        });

        // Hoş geldin sayfasını aç
        chrome.tabs.create({
            url: 'welcome.html'
        });
    }
});

// Alarm'lar için (otomatik senkronizasyon - gelecekte)
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'autoSync') {
        console.log('Otomatik senkronizasyon başlatılıyor...');
        // Auto sync logic buraya
    }
});
