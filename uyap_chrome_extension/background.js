// Background Service Worker - Basit Versiyon
console.log('🟢 Background Service Worker başlatıldı');

// Ayarları yükle
async function loadSettings() {
    return new Promise((resolve) => {
        chrome.storage.sync.get(['apiUrl'], (result) => {
            resolve({ apiUrl: result.apiUrl || 'http://localhost:5000' });
        });
    });
}

// Mesaj dinleyicisi  
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('📨 Mesaj alındı:', request.action);
    
    if (request.action === 'checkAuth') {
        checkAuth().then(sendResponse);
        return true;
    }
    
    if (request.action === 'importCase') {
        importCase(request.data).then(sendResponse);
        return true;
    }
    
    sendResponse({ success: false, error: 'Unknown action' });
    return false;
});

// Auth check
async function checkAuth() {
    try {
        const settings = await loadSettings();
        const response = await fetch(`${settings.apiUrl}/api/check_auth`, {
            credentials: 'include'
        });
        const data = await response.json();
        return { success: true, authenticated: data.authenticated, user: data.user };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Import case
async function importCase(caseData) {
    console.log('📥 Import başladı');
    try {
        const settings = await loadSettings();
        console.log('🚀 URL:', `${settings.apiUrl}/api/import_from_uyap`);
        
        const response = await fetch(`${settings.apiUrl}/api/import_from_uyap`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(caseData)
        });
        
        console.log('📡 Status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('✅ Başarılı:', result);
        return { success: true, case_id: result.case_id, message: result.message };
    } catch (error) {
        console.error('❌ Hata:', error);
        return { success: false, error: error.message };
    }
}

console.log('✅ Service Worker hazır');
