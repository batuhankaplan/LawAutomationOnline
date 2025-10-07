// Popup JavaScript - UI Logic

let currentCases = [];
let selectedCases = new Set();
let settings = {};

console.log('Popup.js yükleniyor...');

// DOM Yüklendikten sonra
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOMContentLoaded event tetiklendi');

    try {
        // Ayarları yükle
        await loadSettings();
        console.log('Ayarlar yüklendi:', settings);

        // Event listener'lar
        initializeEventListeners();
        console.log('Event listeners başlatıldı');

        // Auth kontrolü
        await checkAuthentication();

        // UYAP sayfası kontrolü
        await checkUyapPage();

    } catch (error) {
        console.error('Popup başlatma hatası:', error);
        showError('Extension başlatılamadı: ' + error.message);
    }
});

// Ayarları yükle
async function loadSettings() {
    return new Promise((resolve) => {
        chrome.storage.sync.get(['apiUrl', 'autoSync'], (result) => {
            settings = {
                apiUrl: result.apiUrl || 'http://localhost:5000',
                autoSync: result.autoSync || false
            };

            // Settings tab'ına doldur
            const apiUrlInput = document.getElementById('apiUrl');
            const autoSyncCheckbox = document.getElementById('autoSync');

            if (apiUrlInput) apiUrlInput.value = settings.apiUrl;
            if (autoSyncCheckbox) autoSyncCheckbox.checked = settings.autoSync;

            resolve();
        });
    });
}

// Authentication kontrolü
async function checkAuthentication() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'checkAuth' });

        if (response && response.success && response.authenticated) {
            updateStatus('online', `Bağlı (${response.user?.name || 'Kullanıcı'})`);
            hideElement('authWarning');
        } else {
            updateStatus('error', 'Giriş gerekli');
            showElement('authWarning');
        }
    } catch (error) {
        console.error('Auth check error:', error);
        updateStatus('error', 'Bağlantı hatası');
        showElement('authWarning');
    }
}

// UYAP sayfası kontrolü
async function checkUyapPage() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        if (!tab || !tab.url) {
            console.log('Aktif tab bulunamadı');
            return { isUyap: false, isDetailPage: false };
        }

        if (!tab.url.includes('uyap.gov.tr')) {
            showElement('uyapWarning');
            return { isUyap: false, isDetailPage: false };
        }

        hideElement('uyapWarning');

        // Detay sayfası mı kontrol et
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'checkPageType' });
        const isDetailPage = response && response.isDetailPage;

        console.log('Sayfa tipi:', isDetailPage ? 'Detay Sayfası' : 'Liste Sayfası');

        // UI'ı sayfa tipine göre ayarla
        if (isDetailPage) {
            showElement('detailPageSection');
            hideElement('caseListSection');
        } else {
            hideElement('detailPageSection');
            showElement('caseListSection');
        }

        return { isUyap: true, isDetailPage };
    } catch (error) {
        console.error('Page check error:', error);
        return { isUyap: false, isDetailPage: false };
    }
}

// Event Listeners
function initializeEventListeners() {
    console.log('Event listeners kuruluyor...');

    // Tab değiştirme
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            console.log('Tab tıklandı:', tab.dataset.tab);
            switchTab(tab.dataset.tab);
        });
    });

    // Sayfayı tara butonu
    const scanPageBtn = document.getElementById('scanPageBtn');
    if (scanPageBtn) {
        scanPageBtn.addEventListener('click', () => {
            console.log('Sayfa tara butonuna tıklandı');
            scanCurrentPage();
        });
    }

    // Yenile butonu
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            console.log('Yenile butonuna tıklandı');
            scanCurrentPage();
        });
    }

    // Tümünü seç checkbox
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            console.log('Tümünü seç değişti:', e.target.checked);
            toggleSelectAll(e.target.checked);
        });
    }

    // Seçili dosyaları aktar
    const importSelectedBtn = document.getElementById('importSelectedBtn');
    if (importSelectedBtn) {
        importSelectedBtn.addEventListener('click', () => {
            console.log('Seçili dosyaları aktar butonuna tıklandı');
            importSelectedCases();
        });
    }

    // Detay sayfasından bu dosyayı aktar
    const importCurrentBtn = document.getElementById('importCurrentBtn');
    if (importCurrentBtn) {
        importCurrentBtn.addEventListener('click', () => {
            console.log('Bu dosyayı aktar butonuna tıklandı');
            importCurrentCase();
        });
    }

    // Arama
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterCases(e.target.value);
        });
    }

    // Sistemi aç butonu
    const openSystemBtn = document.getElementById('openSystemBtn');
    if (openSystemBtn) {
        openSystemBtn.addEventListener('click', () => {
            console.log('Sistemi aç butonuna tıklandı');
            chrome.tabs.create({ url: settings.apiUrl });
        });
    }

    // Ayarları kaydet
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            console.log('Ayarları kaydet butonuna tıklandı');
            saveSettings();
        });
    }

    // Bağlantıyı test et
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', () => {
            console.log('Bağlantı test butonuna tıklandı');
            testConnection();
        });
    }

    // Sonuçları kapat
    const closeResultsBtn = document.getElementById('closeResultsBtn');
    if (closeResultsBtn) {
        closeResultsBtn.addEventListener('click', () => {
            hideElement('resultsSection');
        });
    }

    console.log('Tüm event listeners kuruldu');
}

// Tab değiştirme
function switchTab(tabName) {
    console.log('Tab değiştiriliyor:', tabName);

    // Tab butonlarını güncelle
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Tab içeriklerini güncelle
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}Tab`);
    });
}

// Sayfayı tara
async function scanCurrentPage() {
    try {
        console.log('Sayfa taranıyor...');
        updateStatus('online', 'Sayfa taranıyor...');

        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        if (!tab || !tab.id) {
            throw new Error('Aktif tab bulunamadı');
        }

        // UYAP sayfasında olup olmadığını kontrol et
        if (!tab.url || !tab.url.includes('uyap.gov.tr')) {
            throw new Error('Bu sayfa UYAP sayfası değil. Lütfen UYAP Dosya Sorgulama sayfasına gidin.');
        }

        // Content script'in yüklü olup olmadığını kontrol et
        try {
            console.log('Content script ping gönderiliyor...');
            const pingResponse = await chrome.tabs.sendMessage(tab.id, { action: 'ping' });
            console.log('Ping yanıtı:', pingResponse);
        } catch (pingError) {
            console.log('Content script yüklü değil, inject ediliyor...');

            // Content script'i manuel olarak inject et
            try {
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content.js']
                });
                console.log('Content script inject edildi');

                // Script'in yüklenmesi için kısa bir bekleme
                await sleep(500);
            } catch (injectError) {
                console.error('Content script inject hatası:', injectError);
                throw new Error('Content script yüklenemedi. Sayfayı yenileyip tekrar deneyin (F5).');
            }
        }

        // Content script'e mesaj gönder
        console.log('getCaseList mesajı gönderiliyor...');
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'getCaseList' });

        console.log('Content script yanıtı:', response);

        if (response && response.success && response.data) {
            currentCases = response.data;
            console.log('Bulunan dosyalar:', currentCases.length);
            renderCaseList(currentCases);

            if (currentCases.length > 0) {
                showElement('selectAllBar');
                showElement('actionButtons');
            }

            updateStatus('online', `${currentCases.length} dosya bulundu`);
        } else {
            throw new Error('Dosya bulunamadı veya sayfada tablo yok');
        }
    } catch (error) {
        console.error('Tarama hatası:', error);
        updateStatus('error', 'Tarama hatası');
        alert('Sayfa taranırken hata oluştu:\n\n' + error.message + '\n\nYapmanız gerekenler:\n1. UYAP Dosya Sorgulama sayfasında olun\n2. Sayfayı yenileyin (F5)\n3. Tekrar deneyin');
    }
}

// Dosya listesini render et
function renderCaseList(cases) {
    const caseList = document.getElementById('caseList');
    const caseCount = document.getElementById('totalCases');

    if (!caseList || !caseCount) {
        console.error('Case list elementleri bulunamadı');
        return;
    }

    caseCount.textContent = cases.length;

    if (cases.length === 0) {
        caseList.innerHTML = `
            <div class="empty-state">
                <span class="icon">📂</span>
                <p>Dosya bulunamadı</p>
                <button class="btn btn-small btn-primary" id="scanPageBtn2">
                    Sayfayı Tara
                </button>
            </div>
        `;

        // Yeni buton için event listener ekle
        const scanBtn2 = document.getElementById('scanPageBtn2');
        if (scanBtn2) {
            scanBtn2.addEventListener('click', scanCurrentPage);
        }
        return;
    }

    caseList.innerHTML = cases.map((caseData, index) => `
        <div class="case-card" data-index="${index}">
            <div class="case-card-header">
                <input type="checkbox" class="case-checkbox" data-index="${index}">
                <div class="case-card-title">
                    ${caseData.dosyaNo || 'Dosya No Yok'}
                </div>
                <span class="case-badge">${caseData.dosyaTuru || 'Bilinmiyor'}</span>
            </div>
            <div class="case-card-body">
                <p><strong>Birim:</strong> ${caseData.birim || '-'}</p>
                <p><strong>Durum:</strong> ${caseData.dosyaDurumu || '-'}</p>
                ${caseData.acilisTarihi ? `<p><strong>Açılış:</strong> ${caseData.acilisTarihi}</p>` : ''}
            </div>
        </div>
    `).join('');

    // Checkbox event listeners
    document.querySelectorAll('.case-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', handleCaseSelection);
    });
}

// Dosya seçimi
function handleCaseSelection(e) {
    const index = parseInt(e.target.dataset.index);

    if (e.target.checked) {
        selectedCases.add(index);
    } else {
        selectedCases.delete(index);
    }

    updateSelectionUI();
}

// Tümünü seç/bırak
function toggleSelectAll(checked) {
    selectedCases.clear();

    if (checked) {
        currentCases.forEach((_, index) => selectedCases.add(index));
    }

    document.querySelectorAll('.case-checkbox').forEach(checkbox => {
        checkbox.checked = checked;
    });

    updateSelectionUI();
}

// Seçim UI güncelle
function updateSelectionUI() {
    const selectedCount = document.getElementById('selectedCount');
    if (selectedCount) {
        selectedCount.textContent = `${selectedCases.size} seçili`;
    }

    // Tümünü seç checkbox durumu
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = selectedCases.size === currentCases.length && currentCases.length > 0;
        selectAllCheckbox.indeterminate = selectedCases.size > 0 && selectedCases.size < currentCases.length;
    }
}

// Seçili dosyaları aktar
async function importSelectedCases() {
    if (selectedCases.size === 0) {
        alert('Lütfen en az bir dosya seçin');
        return;
    }

    console.log('Seçili dosyalar aktarılıyor:', selectedCases.size);

    // İlerleme göster
    showElement('progressSection');
    hideElement('actionButtons');

    const selectedCaseData = Array.from(selectedCases).map(index => currentCases[index]);
    let imported = 0;
    let failed = 0;

    // Aktif sekmeyi al
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    for (let i = 0; i < selectedCaseData.length; i++) {
        const caseData = selectedCaseData[i];

        try {
            updateProgress(
                (i / selectedCaseData.length) * 100,
                `Dosya aktarılıyor: ${caseData.dosyaNo || (i + 1)}`,
                `${i + 1} / ${selectedCaseData.length}`
            );

            // dosyaNo'yu parse et (örn: "2024/123" -> year: 2024, caseNumber: 123)
            if (caseData.dosyaNo) {
                const match = caseData.dosyaNo.match(/(\d{4})\/(\d+)/);
                if (match) {
                    caseData.year = match[1];
                    caseData.caseNumber = match[2];
                }
            }

            // Detay sayfasını aç (butona tıklayarak)
            console.log('📄 Dosya detayı açılıyor:', caseData.dosyaNo, 'rowId:', caseData.rowId);
            let fullDetails = { caseInfo: caseData, parties: {}, lawyers: [], documents: [], hearings: [] };

            try {
                // Content script'e butona tıklama komutu gönder
                console.log('🖱️ Dosya görüntüle butonuna tıklanıyor...');
                await chrome.tabs.sendMessage(tab.id, {
                    action: 'clickDetailButton',
                    rowId: caseData.rowId,
                    dosyaNo: caseData.dosyaNo
                });

                // Detay sayfası açılana kadar bekle (2 saniye)
                await sleep(2000);

                // Content script'e detay çekme komutu gönder
                console.log('📥 getCaseDetails mesajı gönderiliyor...');
                const detailResponse = await chrome.tabs.sendMessage(tab.id, { action: 'getCaseDetails' });
                console.log('✅ Detay yanıtı:', detailResponse);

                if (detailResponse && detailResponse.success) {
                    fullDetails = detailResponse.data;
                    // Liste sayfasından gelen bilgileri birleştir
                    fullDetails.caseInfo = { ...caseData, ...fullDetails.caseInfo };
                }

                // Geri dön (liste sayfasına)
                console.log('🔙 Liste sayfasına geri dönülüyor...');
                await chrome.tabs.sendMessage(tab.id, { action: 'goBack' });

                // Liste sayfası yüklenene kadar bekle
                await sleep(1500);

            } catch (detailError) {
                console.warn('⚠️ Detay sayfası açılamadı:', detailError);
            }

            // Mapper ile dönüştür
            console.log('Mapper çağrılıyor, fullDetails:', fullDetails);
            const mappedData = mapUyapToSystem(fullDetails);
            console.log('Mapped data:', mappedData);

            // JSON formatında hazırla
            const jsonData = prepareJSON(mappedData);
            console.log('JSON data hazırlandı:', jsonData);

            // Backend'e gönder
            console.log('Backend\'e mesaj gönderiliyor...');

            let response;
            try {
                // Timeout ile mesaj gönder (10 saniye)
                response = await Promise.race([
                    chrome.runtime.sendMessage({
                        action: 'importCase',
                        data: jsonData
                    }),
                    new Promise((_, reject) =>
                        setTimeout(() => reject(new Error('Timeout: Background yanıt vermedi')), 10000)
                    )
                ]);
                console.log('Backend yanıtı:', response);
            } catch (msgError) {
                console.error('❌ Mesaj gönderme hatası:', msgError);
                failed++;
                continue;
            }

            if (response && response.success) {
                imported++;
                console.log('✅ Dosya başarıyla aktarıldı:', caseData.dosyaNo);
            } else {
                failed++;
                console.error('❌ Import hatası:', response?.error || 'Yanıt alınamadı');
            }

            await sleep(500);

        } catch (error) {
            console.error('Dosya aktarma hatası:', error);
            failed++;
        }
    }

    // Tamamlandı
    updateProgress(100, 'Tamamlandı!', `${imported} başarılı, ${failed} hata`);

    // Sonuçları göster
    setTimeout(() => {
        hideElement('progressSection');
        showResults({ total: selectedCaseData.length, success: imported, failed });
    }, 1500);
}

// İlerleme güncelle
function updateProgress(percent, text, detail) {
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressText = document.getElementById('progressText');
    const progressDetail = document.getElementById('progressDetail');

    if (progressFill) progressFill.style.width = `${percent}%`;
    if (progressPercent) progressPercent.textContent = `${Math.round(percent)}%`;
    if (progressText) progressText.textContent = text;
    if (progressDetail) progressDetail.textContent = detail || '';
}

// Sonuçları göster
function showResults(summary) {
    const resultsSummary = document.getElementById('resultsSummary');

    if (resultsSummary) {
        resultsSummary.innerHTML = `
            <div class="summary-card success">
                <span class="number">${summary.success}</span>
                <span class="label">Başarılı</span>
            </div>
            <div class="summary-card error">
                <span class="number">${summary.failed}</span>
                <span class="label">Başarısız</span>
            </div>
        `;
    }

    showElement('resultsSection');
    showElement('actionButtons');
}

// Arama/Filtreleme
function filterCases(query) {
    const filtered = currentCases.filter(caseData => {
        const searchText = `${caseData.dosyaNo} ${caseData.birim} ${caseData.dosyaTuru}`.toLowerCase();
        return searchText.includes(query.toLowerCase());
    });

    renderCaseList(filtered);
}

// Ayarları kaydet
async function saveSettings() {
    const apiUrl = document.getElementById('apiUrl').value;
    const autoSync = document.getElementById('autoSync').checked;

    settings = { apiUrl, autoSync };

    await chrome.storage.sync.set(settings);

    alert('Ayarlar kaydedildi');
}

// Bağlantı testi
async function testConnection() {
    const statusDiv = document.getElementById('connectionStatus');
    if (!statusDiv) return;

    statusDiv.textContent = 'Test ediliyor...';
    statusDiv.className = 'connection-status';

    try {
        const response = await chrome.runtime.sendMessage({ action: 'checkAuth' });

        if (response && response.success && response.authenticated) {
            statusDiv.textContent = `✅ Bağlantı başarılı! (${response.user?.name || 'Kullanıcı'})`;
            statusDiv.className = 'connection-status alert-success';
        } else {
            statusDiv.textContent = '⚠️ Bağlantı başarılı ama giriş yapılmamış';
            statusDiv.className = 'connection-status alert-warning';
        }
    } catch (error) {
        statusDiv.textContent = `❌ Bağlantı hatası: ${error.message}`;
        statusDiv.className = 'connection-status alert-danger';
    }
}

// UI Helper Functions
function showElement(id) {
    const element = document.getElementById(id);
    if (element) element.style.display = 'block';
}

function hideElement(id) {
    const element = document.getElementById(id);
    if (element) element.style.display = 'none';
}

function showError(message) {
    console.error('Error:', message);
    alert('Hata: ' + message);
}

// Detay sayfasından mevcut dosyayı aktar
async function importCurrentCase() {
    try {
        console.log('📥 Detay sayfasından dosya aktarımı başlıyor...');

        // Progress göster
        showElement('progressSection');
        hideElement('detailPageSection');
        updateProgress(10, 'Dosya detayları çekiliyor...', '');

        // Aktif sekmeyi al
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // Content script'ten detay bilgilerini çek
        console.log('📥 getCaseDetails mesajı gönderiliyor...');
        const detailResponse = await chrome.tabs.sendMessage(tab.id, { action: 'getCaseDetails' });
        console.log('✅ Detay yanıtı:', detailResponse);

        if (!detailResponse || !detailResponse.success) {
            throw new Error('Dosya detayları çekilemedi');
        }

        updateProgress(40, 'Veriler dönüştürülüyor...', '');

        // Mapper ile dönüştür
        const fullDetails = detailResponse.data;
        console.log('Mapper çağrılıyor, fullDetails:', fullDetails);
        const mappedData = mapUyapToSystem(fullDetails);
        console.log('Mapped data:', mappedData);

        updateProgress(60, 'Backend\'e gönderiliyor...', '');

        // JSON formatında hazırla
        const jsonData = prepareJSON(mappedData);
        console.log('JSON data hazırlandı:', jsonData);

        // Backend'e gönder
        const response = await chrome.runtime.sendMessage({
            action: 'importCase',
            data: jsonData
        });
        console.log('Backend yanıtı:', response);

        if (response && response.success) {
            updateProgress(100, '✅ Dosya başarıyla aktarıldı!', '');
            console.log('✅ Dosya başarıyla aktarıldı');

            // 2 saniye sonra UI'ı sıfırla
            setTimeout(() => {
                hideElement('progressSection');
                showElement('detailPageSection');
            }, 2000);
        } else {
            throw new Error(response?.error || 'Bilinmeyen hata');
        }

    } catch (error) {
        console.error('❌ Dosya aktarma hatası:', error);
        updateProgress(0, '❌ Hata: ' + error.message, '');

        // 3 saniye sonra UI'ı sıfırla
        setTimeout(() => {
            hideElement('progressSection');
            showElement('detailPageSection');
        }, 3000);
    }
}

function updateStatus(type, text) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.getElementById('statusText');

    if (statusDot) {
        statusDot.className = `status-dot ${type === 'error' ? 'error' : ''}`;
    }
    if (statusText) {
        statusText.textContent = text;
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

console.log('Popup.js yüklendi');
