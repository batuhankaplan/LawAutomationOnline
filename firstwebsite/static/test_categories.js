// Kategori yönetimi test scripti - Tarayıcı konsolunda çalıştır
console.log('🔍 Kategori yönetimi test başlatılıyor...');

// 1. DOM elementlerini kontrol et
function testDOMElements() {
    console.log('📋 DOM elementleri kontrol ediliyor...');
    
    const kategoriBox = document.querySelector('.kategori-yonetimi-box');
    const mevcutBox = document.querySelector('.mevcut-kategoriler-box');
    const kategoriGrid = document.querySelector('.kategori-grid');
    const kategoriCards = document.querySelectorAll('.kategori-card-pro');
    
    console.log('Kategori yönetimi box:', kategoriBox ? '✅ Var' : '❌ Yok');
    console.log('Mevcut kategoriler box:', mevcutBox ? '✅ Var' : '❌ Yok');
    console.log('Kategori grid:', kategoriGrid ? '✅ Var' : '❌ Yok');
    console.log('Kategori kartları:', kategoriCards.length + ' adet');
    
    if (mevcutBox) {
        console.log('Mevcut kategoriler box içeriği:', mevcutBox.innerHTML);
    }
    
    return {
        kategoriBox,
        mevcutBox,
        kategoriGrid,
        kategoriCards
    };
}

// 2. API'yi test et
async function testAPI() {
    console.log('🌐 API test ediliyor...');
    
    try {
        const response = await fetch('/api/dilekce_kategorileri');
        console.log('API response status:', response.status);
        
        if (response.status === 200) {
            const data = await response.json();
            console.log('API response data:', data);
            
            if (data.success) {
                console.log('✅ API başarılı');
                console.log('Kategori sayısı:', data.kategoriler?.length || 0);
                
                if (data.kategoriler && data.kategoriler.length > 0) {
                    console.log('Kategoriler:');
                    data.kategoriler.forEach((kat, index) => {
                        console.log(`  ${index + 1}. ${kat.ad} (ID: ${kat.id})`);
                    });
                }
            } else {
                console.log('❌ API hatası:', data.message);
            }
        } else if (response.status === 401) {
            console.log('❌ Yetkilendirme hatası - Giriş yapmanız gerekiyor');
        } else {
            console.log('❌ API hatası:', response.status);
        }
    } catch (error) {
        console.log('❌ Network hatası:', error);
    }
}

// 3. kategorileriListele fonksiyonunu test et
function testKategorileriListele() {
    console.log('⚡ kategorileriListele fonksiyonu test ediliyor...');
    
    if (typeof kategorileriListele === 'function') {
        console.log('✅ kategorileriListele fonksiyonu mevcut');
        
        // Fonksiyonu çağır
        kategorileriListele()
            .then(() => {
                console.log('✅ kategorileriListele başarıyla çalıştırıldı');
                
                // DOM'u yeniden kontrol et
                setTimeout(() => {
                    const updatedCards = document.querySelectorAll('.kategori-card-pro');
                    console.log('Güncellenmiş kategori kartları:', updatedCards.length + ' adet');
                }, 1000);
            })
            .catch(error => {
                console.log('❌ kategorileriListele hatası:', error);
            });
    } else {
        console.log('❌ kategorileriListele fonksiyonu bulunamadı');
    }
}

// 4. CSS stillerini kontrol et
function testCSS() {
    console.log('🎨 CSS stilleri kontrol ediliyor...');
    
    const mevcutBox = document.querySelector('.mevcut-kategoriler-box');
    if (mevcutBox) {
        const computedStyles = window.getComputedStyle(mevcutBox);
        console.log('Mevcut kategoriler box stilleri:');
        console.log('  Display:', computedStyles.display);
        console.log('  Visibility:', computedStyles.visibility);
        console.log('  Background:', computedStyles.background);
        console.log('  Padding:', computedStyles.padding);
        console.log('  Min-height:', computedStyles.minHeight);
    }
}

// 5. Tam test süreci
async function fullTest() {
    console.log('🚀 Tam test süreci başlatılıyor...');
    
    // 1. DOM kontrolü
    const domResults = testDOMElements();
    
    // 2. API testi
    await testAPI();
    
    // 3. CSS kontrolü
    testCSS();
    
    // 4. Fonksiyon testi
    testKategorileriListele();
    
    console.log('✅ Test tamamlandı!');
}

// Ana test fonksiyonu
window.testCategories = fullTest;

// Test'i hemen çalıştır
fullTest();