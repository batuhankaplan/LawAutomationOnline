// Popup JavaScript - UI Logic

let currentCases = [];
let selectedCases = new Set();
let settings = {};

// DOM Yüklendikten sonra
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Popup yüklendi');

    // Ayarları yükle
    await loadSettings();

    // Auth kontrolü
    await checkAuthentication();

    // Event listener'lar
    initializeEventListeners();

    // UYAP sayfası kontrolü
    checkUyapPage();
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
            document.getElementById('apiUrl').value = settings.apiUrl;
            document.getElementById('autoSync').checked = settings.autoSync;

            resolve();
        });
    });
}

// Authentication kontrolü
async function checkAuthentication() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'checkAuth' });

        if (response.success && response.authenticated) {
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

        if (!tab.url.includes('uyap.gov.tr')) {
            showElement('uyapWarning');
            return false;
        }

        hideElement('uyapWarning');
        return true;
    } catch (error) {
        console.error('Page check error:', error);
        return false;
    }
}

// Event Listeners
function initializeEventListeners() {
    // Tab değiştirme
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Sayfayı tara butonu
    document.getElementById('scanPageBtn').addEventListener('click', scanCurrentPage);

    // Yenile butonu
    document.getElementById('refreshBtn').addEventListener('click', scanCurrentPage);

    // Tümünü seç checkbox
    document.getElementById('selectAllCheckbox').addEventListener('change', (e) => {
        toggleSelectAll(e.target.checked);
    });

    // Seçili dosyaları aktar
    document.getElementById('importSelectedBtn').addEventListener('click', importSelectedCases);

    // Arama
    document.getElementById('searchInput').addEventListener('input', (e) => {
        filterCases(e.target.value);
    });

    // Sistemi aç butonu
    document.getElementById('openSystemBtn').addEventListener('click', () => {
        chrome.tabs.create({ url: settings.apiUrl });
    });

    // Ayarlar
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    document.getElementById('testConnectionBtn').addEventListener('click', testConnection);

    // Sonuçları kapat
    document.getElementById('closeResultsBtn').addEventListener('click', () => {
        hideElement('resultsSection');
    });
}

// Tab değiştirme
function switchTab(tabName) {
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
        showLoading('Sayfa taranıyor...');

        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // Content script'e mesaj gönder
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'getCaseList' });

        if (response.success && response.data) {
            currentCases = response.data;
            renderCaseList(currentCases);

            if (currentCases.length > 0) {
                showElement('selectAllBar');
                showElement('actionButtons');
            }

            hideLoading();
        } else {
            throw new Error('Dosya bulunamadı');
        }
    } catch (error) {
        console.error('Tarama hatası:', error);
        showError('Sayfa taranırken hata oluştu: ' + error.message);
        hideLoading();
    }
}

// Dosya listesini render et
function renderCaseList(cases) {
    const caseList = document.getElementById('caseList');
    const caseCount = document.getElementById('totalCases');

    caseCount.textContent = cases.length;

    if (cases.length === 0) {
        caseList.innerHTML = `
            <div class="empty-state">
                <span class="icon">📂</span>
                <p>Dosya bulunamadı</p>
                <button class="btn btn-small btn-primary" id="scanPageBtn">
                    Sayfayı Tara
                </button>
            </div>
        `;
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

    // Card click - detay getir
    document.querySelectorAll('.case-card').forEach(card => {
        card.addEventListener('click', async (e) => {
            if (e.target.type !== 'checkbox') {
                const index = card.dataset.index;
                await fetchCaseDetails(currentCases[index]);
            }
        });
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
    selectedCount.textContent = `${selectedCases.size} seçili`;

    // Tümünü seç checkbox durumu
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    selectAllCheckbox.checked = selectedCases.size === currentCases.length && currentCases.length > 0;
    selectAllCheckbox.indeterminate = selectedCases.size > 0 && selectedCases.size < currentCases.length;
}

// Dosya detaylarını getir
async function fetchCaseDetails(caseData) {
    try {
        showLoading('Dosya detayları getiriliyor...');

        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // Detay sayfasına git (eğer URL varsa)
        if (caseData.detailUrl) {
            await chrome.tabs.update(tab.id, { url: caseData.detailUrl });

            // Sayfa yüklenene kadar bekle
            await sleep(2000);
        }

        // Detayları çek
        const response = await chrome.tabs.sendMessage(tab.id, { action: 'getCaseDetails' });

        if (response.success && response.data) {
            // Detayları case data'ya ekle
            Object.assign(caseData, response.data);
            hideLoading();
        }

    } catch (error) {
        console.error('Detay getirme hatası:', error);
        hideLoading();
    }
}

// Seçili dosyaları aktar
async function importSelectedCases() {
    if (selectedCases.size === 0) {
        showError('Lütfen en az bir dosya seçin');
        return;
    }

    // İlerleme göster
    showElement('progressSection');
    hideElement('actionButtons');

    const selectedCaseData = Array.from(selectedCases).map(index => currentCases[index]);
    let imported = 0;
    let failed = 0;

    for (let i = 0; i < selectedCaseData.length; i++) {
        const caseData = selectedCaseData[i];

        try {
            updateProgress((i / selectedCaseData.length) * 100,
                          `Dosya aktarılıyor: ${caseData.dosyaNo || (i+1)}`,
                          `${i + 1} / ${selectedCaseData.length}`);

            // Detayları çek
            await fetchCaseDetails(caseData);

            // Mapper ile dönüştür
            const mappedData = mapUyapToSystem(caseData);

            // Backend'e gönder
            const response = await chrome.runtime.sendMessage({
                action: 'importCase',
                data: mappedData
            });

            if (response.success) {
                imported++;
            } else {
                failed++;
                console.error('Import hatası:', response.error);
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
    document.getElementById('progressFill').style.width = `${percent}%`;
    document.getElementById('progressPercent').textContent = `${Math.round(percent)}%`;
    document.getElementById('progressText').textContent = text;
    document.getElementById('progressDetail').textContent = detail || '';
}

// Sonuçları göster
function showResults(summary) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsSummary = document.getElementById('resultsSummary');

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

    showSuccess('Ayarlar kaydedildi');
}

// Bağlantı testi
async function testConnection() {
    const statusDiv = document.getElementById('connectionStatus');
    statusDiv.textContent = 'Test ediliyor...';
    statusDiv.className = 'connection-status';

    try {
        const response = await chrome.runtime.sendMessage({ action: 'checkAuth' });

        if (response.success && response.authenticated) {
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
    document.getElementById(id).style.display = 'block';
}

function hideElement(id) {
    document.getElementById(id).style.display = 'none';
}

function showLoading(message) {
    // TODO: Implement loading overlay
    console.log('Loading:', message);
}

function hideLoading() {
    // TODO: Hide loading overlay
    console.log('Loading complete');
}

function showError(message) {
    // TODO: Implement toast notification
    alert('Hata: ' + message);
}

function showSuccess(message) {
    // TODO: Implement toast notification
    alert('Başarılı: ' + message);
}

function updateStatus(type, text) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.getElementById('statusText');

    statusDot.className = `status-dot ${type === 'error' ? 'error' : ''}`;
    statusText.textContent = text;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
