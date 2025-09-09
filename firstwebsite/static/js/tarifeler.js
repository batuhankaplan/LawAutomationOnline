document.addEventListener('DOMContentLoaded', function () {
    const tarifeApiUrl = '/api/tarifeler';
    const tarifeTabContent = document.getElementById('tarifeTabContent');
    
    // Kaplan Danışmanlık için yeni DOM elementleri
    const kaplanDanismanlikListeContainer = document.getElementById('kaplan-danismanlik-liste-container');
    const kaplanDanismanlikEditorContainer = document.getElementById('kaplan-danismanlik-editor-container');
    const kaplanDanismanlikEditorContent = document.getElementById('kaplan-danismanlik-editor-content'); // Editörün içeriğinin render edileceği yer
    
    // Yeni Buton Grupları ve Butonlar
    const kaplanDuzenleBtnGroup = document.getElementById('kaplan-danismanlik-duzenle-btn-group');
    const kaplanDuzenleBtn = document.getElementById('kaplan-danismanlik-duzenle-btn'); // Bu artık alttaki büyük buton
    const kaplanKaydetBtnGroup = document.getElementById('kaplan-danismanlik-kaydet-btn-group');
    const kaplanIptalBtn = document.getElementById('kaplan-danismanlik-iptal-btn');
    const kaydetKaplanDanismanlikTarifeBtn = document.getElementById('kaydet-kaplan-danismanlik-tarife');

    let kaplanDanismanlikTarifeData = { kategoriler: [] };
    let isKaplanEditModeActive = false; // Kaplan sekmesi için edit modu state'i

    const tarifeGrupMap = {
        "İstanbul Barosu": {
            id: "istbaro-content",
            label: "İstanbul Barosu Tavsiye Ücret Tarifesi 2025",
            cols: ["Hizmet Adı", "Temel Ücret"]
        },
        "TBB": {
            id: "tbb-content",
            label: "TBB Avukatlık Asgari Ücret Tarifesi 2025",
            cols: ["Hizmet Adı", "Temel Ücret"]
        }
    };
    
    const grupSiralama = ["İstanbul Barosu", "TBB"];

    // Toast bildirimleri için yardımcı fonksiyon
    function showToast(title, message, type = 'info') {
        let toastContainer = document.getElementById('toastPlacement');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastPlacement';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1055'; // Modal'ların üzerinde olması için
            document.body.appendChild(toastContainer);
        }

        const toastId = 'toast-' + Date.now();
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type === 'danger' ? 'danger' : (type === 'success' ? 'success' : 'primary')} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong> ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
        toast.show();
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    function formatCurrency(amount, currency = 'TRY') {
        try {
            const numericAmount = parseFloat(String(amount).replace(/[^0-9.-]+/g, ""));
            if (isNaN(numericAmount)) {
                return String(amount);
            }
            return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: currency, minimumFractionDigits: 2 }).format(numericAmount);
        } catch (e) {
            return String(amount);
        }
    }

    async function fetchTarifeler() {
        try {
            const response = await fetch(tarifeApiUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            renderStaticTarifeler(data); // İstBaro ve TBB için

            if (data.kaplan_danismanlik_tarifesi && typeof data.kaplan_danismanlik_tarifesi === 'object') {
                kaplanDanismanlikTarifeData = JSON.parse(JSON.stringify(data.kaplan_danismanlik_tarifesi)); 
                if (!kaplanDanismanlikTarifeData.kategoriler || !Array.isArray(kaplanDanismanlikTarifeData.kategoriler)) {
                     kaplanDanismanlikTarifeData.kategoriler = [];
                }
            } else {
                kaplanDanismanlikTarifeData = { kategoriler: [] };
            }
            
            // Edit moduna göre uygun Kaplan render fonksiyonunu çağır
            renderKaplanDanismanlikSection();

        } catch (error) {
            console.error("Tarifeler yüklenirken hata oluştu:", error);
            if (tarifeTabContent) {
                tarifeTabContent.innerHTML = '<div class="alert alert-danger" role="alert">Tarifeler yüklenirken bir sorun oluştu. Lütfen daha sonra tekrar deneyin.</div>';
            }
             if (kaplanDanismanlikListeContainer) {
                kaplanDanismanlikListeContainer.innerHTML = '<div class="alert alert-danger" role="alert">Kaplan Hukuk Danışmanlık tarifesi yüklenirken bir sorun oluştu.</div>';
            }
            if (kaplanDanismanlikEditorContent) {
                kaplanDanismanlikEditorContent.innerHTML = '<div class="alert alert-danger" role="alert">Danışmanlık tarifesi editörü yüklenirken bir sorun oluştu.</div>';
            }
        }
    }

    function renderStaticTarifeler(tarifelerData) {
        if (!tarifeTabContent) return;

        grupSiralama.forEach(tarifeGrubuKey => {
            if (tarifeGrupMap.hasOwnProperty(tarifeGrubuKey) && tarifelerData.hasOwnProperty(tarifeGrubuKey)) {
                const grupBilgisi = tarifeGrupMap[tarifeGrubuKey];
                const kategorilerData = tarifelerData[tarifeGrubuKey];
                const contentDiv = document.getElementById(grupBilgisi.id);
                
                if (contentDiv) {
                    contentDiv.innerHTML = ''; 
                    if (kategorilerData && kategorilerData.length > 0) {
                        const mainTable = document.createElement('table');
                        mainTable.className = 'table table-striped table-hover tarife-tablosu';
                        
                        const thead = document.createElement('thead');
                        const headerRow = document.createElement('tr');
                        grupBilgisi.cols.forEach(colName => {
                            const th = document.createElement('th');
                            th.textContent = colName;
                            headerRow.appendChild(th);
                        });
                        thead.appendChild(headerRow);
                        mainTable.appendChild(thead);

                        const tbody = document.createElement('tbody');

                        kategorilerData.forEach(kategoriObj => {
                            const kategoriAdi = kategoriObj.kategori;
                            const tarifeItems = kategoriObj.items;

                            if (kategoriAdi && tarifeItems && tarifeItems.length > 0) {
                                const kategoriBaslikTr = document.createElement('tr');
                                kategoriBaslikTr.className = 'tarife-kategori-baslik-satiri';
                                const kategoriBaslikTd = document.createElement('td');
                                kategoriBaslikTd.colSpan = grupBilgisi.cols.length;
                                kategoriBaslikTd.innerHTML = `<h3>${kategoriAdi}</h3>`;
                                kategoriBaslikTr.appendChild(kategoriBaslikTd);
                                tbody.appendChild(kategoriBaslikTr);

                                tarifeItems.forEach(tarife => {
                                    const satirTr = createStaticTarifeSatiri(tarife, tarifeGrubuKey, grupBilgisi.cols);
                                    tbody.appendChild(satirTr);
                                });
                            }
                        });
                        mainTable.appendChild(tbody);
                        contentDiv.appendChild(mainTable);

                    } else {
                        contentDiv.innerHTML = '<div class="alert alert-info" role="alert">Bu grup için gösterilecek tarife bulunmamaktadır.</div>';
                    }
                }
            } else if (tarifeGrupMap.hasOwnProperty(tarifeGrubuKey)) {
                 const grupBilgisi = tarifeGrupMap[tarifeGrubuKey];
                 const contentDiv = document.getElementById(grupBilgisi.id);
                 if (contentDiv && (contentDiv.innerHTML === '' || contentDiv.querySelector('.tarifeler-page-loader'))) {
                    contentDiv.innerHTML = '<div class="alert alert-info" role="alert">Bu grup için veri bulunamadı.</div>';
                 }
            }
        });
        document.querySelectorAll('.tarifeler-page-loader').forEach(loader => loader.remove());
    }

    function createStaticTarifeSatiri(tarife, tarifeGrubuKey, cols) {
        const satirTr = document.createElement('tr');
        satirTr.id = `tarife-satir-${tarife.hizmet_adi ? String(tarife.hizmet_adi).replace(/\W/g, '_') : Date.now()}`;

        const hizmetAdiTd = document.createElement('td');
        hizmetAdiTd.textContent = tarife.hizmet_adi || 'N/A';
        satirTr.appendChild(hizmetAdiTd);
        
        let ucretGosterim = 'N/A';
        if (tarife.temel_ucret) {
            const ucretStr = String(tarife.temel_ucret);
            const ucretMatch = ucretStr.match(/([\d.,]+)\s*(\S*)/);
            let numericAmount = parseFloat(ucretStr.replace(/[^0-9.,]/g, '').replace(',', '.'));
            let currencyLabel = "TRY"; 
            
            if(ucretMatch && ucretMatch[2]){
                currencyLabel = ucretMatch[2].toUpperCase();
            }
            
            if (!isNaN(numericAmount)) {
                 if (tarife.birim === '%') { 
                    ucretGosterim = `${numericAmount}%`;
                } else if (currencyLabel && currencyLabel !== 'TRY' && currencyLabel !== 'TL') { 
                    ucretGosterim = `${formatCurrency(numericAmount, "TRY")} / ${currencyLabel}`;
                } else { 
                    ucretGosterim = formatCurrency(numericAmount, "TRY");
                }
            } else {
                 ucretGosterim = ucretStr;
            }
        }

        let ekNotAciklama = '';
        if (tarife.ek_not) {
            ekNotAciklama = ` <span class="text-muted fst-italic">(${tarife.ek_not})</span>`;
        }
        
        const temelUcretTd = document.createElement('td');
        temelUcretTd.innerHTML = `${ucretGosterim}${ekNotAciklama}`;
        satirTr.appendChild(temelUcretTd);
        return satirTr;
    }
    
    // Kaplan Danışmanlık bölümünü yöneten ana fonksiyon
    function renderKaplanDanismanlikSection() {
        if (isKaplanEditModeActive) {
            kaplanDanismanlikListeContainer.style.display = 'none';
            kaplanDanismanlikEditorContainer.style.display = 'block';
            kaplanDuzenleBtnGroup.style.display = 'none'; // "Tarifeyi Düzenle" buton grubunu gizle
            kaplanKaydetBtnGroup.style.display = 'block'; // "Kaydet/İptal" buton grubunu göster
            renderKaplanDanismanlikEditor();
        } else {
            kaplanDanismanlikListeContainer.style.display = 'block';
            kaplanDanismanlikEditorContainer.style.display = 'none';
            kaplanDuzenleBtnGroup.style.display = 'block'; // "Tarifeyi Düzenle" buton grubunu göster
            kaplanKaydetBtnGroup.style.display = 'none'; // "Kaydet/İptal" buton grubunu gizle
            renderKaplanDanismanlikStaticList();
        }
    }

    // Kaplan Danışmanlık için Salt Okunur Liste Oluşturma Fonksiyonu
    function renderKaplanDanismanlikStaticList() {
        if (!kaplanDanismanlikListeContainer) return;
        kaplanDanismanlikListeContainer.innerHTML = '';

        if (!kaplanDanismanlikTarifeData || !kaplanDanismanlikTarifeData.kategoriler || kaplanDanismanlikTarifeData.kategoriler.length === 0) {
            kaplanDanismanlikListeContainer.innerHTML = '<div class="alert alert-info">Henüz Kaplan Hukuk Danışmanlık için bir tarife eklenmemiş. Düzenle butonuna tıklayarak ekleyebilirsiniz.</div>';
            return;
        }

        const mainTable = document.createElement('table');
        mainTable.className = 'table table-striped table-hover tarife-tablosu kaplan-hukuk-tarife-tablosu';
        
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ["Hizmet Adı", "Temel Ücret"].forEach(colName => {
            const th = document.createElement('th');
            th.textContent = colName;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        mainTable.appendChild(thead);

        const tbody = document.createElement('tbody');
        kaplanDanismanlikTarifeData.kategoriler.forEach(kategori => {
            const kategoriBaslikTr = document.createElement('tr');
            kategoriBaslikTr.className = 'tarife-kategori-baslik-satiri';
            const kategoriBaslikTd = document.createElement('td');
            kategoriBaslikTd.colSpan = 2;
            kategoriBaslikTd.innerHTML = `<h3>${kategori.kategoriAdi || 'Kategorisiz'}</h3>`;
            kategoriBaslikTr.appendChild(kategoriBaslikTd);
            tbody.appendChild(kategoriBaslikTr);

            if (kategori.hizmetler && kategori.hizmetler.length > 0) {
                kategori.hizmetler.forEach(hizmet => {
                    const satirTr = document.createElement('tr');
                    
                    const hizmetAdiTd = document.createElement('td');
                    hizmetAdiTd.textContent = hizmet.hizmetAdi || 'N/A';
                    satirTr.appendChild(hizmetAdiTd);

                    const temelUcretTd = document.createElement('td');
                    let ucretGosterim = hizmet.temelUcret ? formatCurrency(hizmet.temelUcret) : 'N/A';
                    let ekNotGosterim = '';
                    if (hizmet.ekNot) {
                        ekNotGosterim = ` <span class="text-muted fst-italic">(${hizmet.ekNot})</span>`;
                    }
                    temelUcretTd.innerHTML = ucretGosterim + ekNotGosterim;
                    satirTr.appendChild(temelUcretTd);

                    tbody.appendChild(satirTr);

                    // Ekstraları, aynı satırda - HİZMET ADI hücresinin altında (alt konu gibi) göster
                    if (hizmet.ekstralar && hizmet.ekstralar.length > 0) {
                        const ekstraWrapper = document.createElement('div');
                        ekstraWrapper.className = 'kaplan-ekstralar-container-compact ekstra-inline-under-name';
                        const ekstraList = document.createElement('ul');
                        ekstraList.className = 'list-unstyled mb-0 small text-muted';
                        hizmet.ekstralar.forEach(ekstra => {
                            const li = document.createElement('li');
                            li.innerHTML = `<strong>${ekstra.aciklama || 'Ekstra'}:</strong> ${ekstra.tutar ? formatCurrency(ekstra.tutar) : 'N/A'}`;
                            ekstraList.appendChild(li);
                        });
                        ekstraWrapper.appendChild(ekstraList);
                        // Hizmet adı hücresinin altına ekle (aynı satırda alt konu gibi)
                        hizmetAdiTd.appendChild(ekstraWrapper);
                    }
                });
            } else {
                const bosHizmetTr = document.createElement('tr');
                const bosHizmetTd = document.createElement('td');
                bosHizmetTd.colSpan = 2; // Colspan 2'ye düşürüldü
                bosHizmetTd.textContent = 'Bu kategoride hizmet bulunmamaktadır.';
                bosHizmetTd.className = 'text-muted text-center p-3';
                bosHizmetTr.appendChild(bosHizmetTd);
                tbody.appendChild(bosHizmetTr);
            }
        });
        mainTable.appendChild(tbody);
        kaplanDanismanlikListeContainer.appendChild(mainTable);
    }

    function renderKaplanDanismanlikEditor() {
        if (!kaplanDanismanlikEditorContent) return;
        kaplanDanismanlikEditorContent.innerHTML = ''; // Önceki editör içeriğini temizle
        const fragment = document.createDocumentFragment();

        const yeniKategoriBtnWrapper = document.createElement('div');
        yeniKategoriBtnWrapper.className = 'mb-3';
        const yeniKategoriBtn = document.createElement('button');
        yeniKategoriBtn.className = 'btn btn-primary';
        yeniKategoriBtn.innerHTML = '<i class="fas fa-plus me-2"></i>Yeni Dava Türü (Kategori) Ekle';
        yeniKategoriBtn.addEventListener('click', handleAddNewCategory);
        yeniKategoriBtnWrapper.appendChild(yeniKategoriBtn);
        fragment.appendChild(yeniKategoriBtnWrapper);

        if (!kaplanDanismanlikTarifeData || !kaplanDanismanlikTarifeData.kategoriler || kaplanDanismanlikTarifeData.kategoriler.length === 0) {
            const emptyMsg = document.createElement('div');
            emptyMsg.className = 'alert alert-info';
            emptyMsg.textContent = 'Henüz bir danışmanlık ücret kategorisi (Dava Türü) eklenmemiş. Yukarıdaki butonu kullanarak başlayabilirsiniz.';
            fragment.appendChild(emptyMsg);
        } else {
            kaplanDanismanlikTarifeData.kategoriler.forEach((kategori, kategoriIndex) => {
                fragment.appendChild(createCategoryElement(kategori, kategoriIndex));
            });
        }
        kaplanDanismanlikEditorContent.appendChild(fragment);
    }

    function createCategoryElement(kategori, kategoriIndex) {
        const kategoriDiv = document.createElement('div');
        kategoriDiv.className = 'tarife-kategori-editor card mb-3';
        kategoriDiv.dataset.kategoriId = kategori.id;

        const cardHeader = document.createElement('div');
        cardHeader.className = 'card-header d-flex justify-content-between align-items-center';
        
        const kategoriAdiInput = document.createElement('input');
        kategoriAdiInput.type = 'text';
        kategoriAdiInput.className = 'form-control form-control-sm me-2 flex-grow-1';
        kategoriAdiInput.value = kategori.kategoriAdi || '';
        kategoriAdiInput.placeholder = 'Kategori Adı (örn: Danışmanlık Hizmetleri)';
        kategoriAdiInput.addEventListener('input', (e) => {
            kategori.kategoriAdi = e.target.value;
        });
        
        const kategoriKontrolleri = document.createElement('div');
        kategoriKontrolleri.className = 'btn-group btn-group-sm';

        const yukariBtn = createIconButton('fas fa-arrow-up', () => handleMoveCategory(kategoriIndex, -1), 'Yukarı Taşı', 'btn-outline-secondary', kategoriIndex === 0);
        const asagiBtn = createIconButton('fas fa-arrow-down', () => handleMoveCategory(kategoriIndex, 1), 'Aşağı Taşı', 'btn-outline-secondary', kategoriIndex === kaplanDanismanlikTarifeData.kategoriler.length - 1);
        const silBtn = createIconButton('fas fa-trash-alt', () => handleDeleteCategory(kategoriIndex, kategori.id), 'Kategoriyi Sil', 'btn-outline-danger');
        
        kategoriKontrolleri.append(yukariBtn, asagiBtn, silBtn);
        cardHeader.append(kategoriAdiInput, kategoriKontrolleri);
        kategoriDiv.appendChild(cardHeader);

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';

        const hizmetlerContainer = document.createElement('div');
        hizmetlerContainer.className = 'hizmetler-container mt-2';
        if (kategori.hizmetler && kategori.hizmetler.length > 0) {
            kategori.hizmetler.forEach((hizmet, hizmetIndex) => {
                hizmetlerContainer.appendChild(createServiceElement(hizmet, kategori.id, hizmetIndex));
            });
        } else {
            hizmetlerContainer.innerHTML = '<p class="text-muted small">Bu kategoride henüz hizmet yok.</p>';
        }
        cardBody.appendChild(hizmetlerContainer);
        
        const yeniHizmetBtn = document.createElement('button');
        yeniHizmetBtn.className = 'btn btn-success btn-sm mt-2';
        yeniHizmetBtn.innerHTML = '<i class="fas fa-plus me-1"></i>Bu Kategoriye Hizmet Ekle';
        yeniHizmetBtn.addEventListener('click', () => handleAddNewService(kategoriIndex, kategori.id));
        cardBody.appendChild(yeniHizmetBtn);

        kategoriDiv.appendChild(cardBody);
        return kategoriDiv;
    }

    function handleAddNewCategory() {
        const newCategoryId = 'kategori_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
        const newCategory = {
            id: newCategoryId,
            kategoriAdi: '',
            sira: kaplanDanismanlikTarifeData.kategoriler.length + 1,
            hizmetler: []
        };
        kaplanDanismanlikTarifeData.kategoriler.push(newCategory);
        renderKaplanDanismanlikEditor(); // Sadece editör içini yeniden çiz
    }

    function handleDeleteCategory(kategoriIndex, kategoriId) {
        const kategoriAdi = kaplanDanismanlikTarifeData.kategoriler[kategoriIndex].kategoriAdi || 'Bu';
        if (confirm(`"${kategoriAdi}" kategorisini ve içindeki tüm hizmetleri silmek istediğinizden emin misiniz?`)) {
            kaplanDanismanlikTarifeData.kategoriler.splice(kategoriIndex, 1);
            kaplanDanismanlikTarifeData.kategoriler.forEach((kat, idx) => kat.sira = idx + 1);
            renderKaplanDanismanlikEditor(); // Sadece editör içini yeniden çiz
        }
    }

    function handleMoveCategory(kategoriIndex, direction) {
        const kategoriler = kaplanDanismanlikTarifeData.kategoriler;
        const newIndex = kategoriIndex + direction;
        if (newIndex < 0 || newIndex >= kategoriler.length) return;

        [kategoriler[kategoriIndex], kategoriler[newIndex]] = [kategoriler[newIndex], kategoriler[kategoriIndex]];
        kategoriler.forEach((kat, idx) => kat.sira = idx + 1);
        renderKaplanDanismanlikEditor(); // Sadece editör içini yeniden çiz
    }
    
    function handleAddNewService(kategoriIndex, kategoriId) {
        const kategori = kaplanDanismanlikTarifeData.kategoriler[kategoriIndex];
        if (!kategori) return;
        if (!kategori.hizmetler) kategori.hizmetler = [];

        const newServiceId = 'hizmet_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
        const newService = {
            id: newServiceId,
            hizmetAdi: '',
            temelUcret: '',
            ekNot: '',
            ekstralar: [],
            sira: kategori.hizmetler.length + 1
        };
        kategori.hizmetler.push(newService);
        renderKaplanDanismanlikEditor(); // Sadece editör içini yeniden çiz
    }

    function handleDeleteService(kategoriId, hizmetIndex, hizmetId) {
         const kategori = kaplanDanismanlikTarifeData.kategoriler.find(k => k.id === kategoriId);
         if (!kategori || !kategori.hizmetler) return;
         const hizmetAdi = kategori.hizmetler[hizmetIndex].hizmetAdi || 'Bu hizmet';
        if (confirm(`"${hizmetAdi}" hizmetini silmek istediğinizden emin misiniz?`)) {
            kategori.hizmetler.splice(hizmetIndex, 1);
            kategori.hizmetler.forEach((h, idx) => h.sira = idx + 1);
            renderKaplanDanismanlikEditor(); // Sadece editör içini yeniden çiz
        }
    }

    function handleMoveService(kategoriId, hizmetIndex, direction) {
        const kategori = kaplanDanismanlikTarifeData.kategoriler.find(k => k.id === kategoriId);
        if (!kategori || !kategori.hizmetler) return;
        const hizmetler = kategori.hizmetler;
        const newIndex = hizmetIndex + direction;
        if (newIndex < 0 || newIndex >= hizmetler.length) return;

        [hizmetler[hizmetIndex], hizmetler[newIndex]] = [hizmetler[newIndex], hizmetler[hizmetIndex]];
        hizmetler.forEach((h, idx) => h.sira = idx + 1);
        renderKaplanDanismanlikEditor();
    }

    function createServiceElement(hizmet, kategoriId, hizmetIndex) {
        const hizmetDiv = document.createElement('div');
        hizmetDiv.className = 'tarife-hizmet-editor card card-body mb-2';
        hizmetDiv.dataset.hizmetId = hizmet.id;
        hizmetDiv.dataset.kategoriId = kategoriId;

        const hizmetAdiRow = document.createElement('div');
        hizmetAdiRow.className = 'row mb-2 align-items-center';
        const hizmetAdiLabelCol = createLabelCol('Hizmet Adı:');
        const hizmetAdiInputCol = createInputCol();
        const hizmetAdiInput = createTextInput(hizmet.hizmetAdi || '', 'örn: Marka Tescil Başvurusu', (val) => hizmet.hizmetAdi = val);
        hizmetAdiInputCol.appendChild(hizmetAdiInput);
        hizmetAdiRow.append(hizmetAdiLabelCol, hizmetAdiInputCol);
        
        const temelUcretRow = document.createElement('div');
        temelUcretRow.className = 'row mb-2 align-items-center';
        const temelUcretLabelCol = createLabelCol('Temel Ücret (örn: 2500 TRY):');
        const temelUcretInputCol = createInputCol();
        const temelUcretInput = createTextInput(hizmet.temelUcret || '', 'örn: 2500 TRY veya 150 USD', (val) => hizmet.temelUcret = val);
        temelUcretInputCol.appendChild(temelUcretInput);
        temelUcretRow.append(temelUcretLabelCol, temelUcretInputCol);

        const ekNotRow = document.createElement('div');
        ekNotRow.className = 'row mb-2 align-items-center';
        const ekNotLabelCol = createLabelCol('Ek Not (opsiyonel):');
        const ekNotInputCol = createInputCol();
        const ekNotTextarea = document.createElement('textarea');
        ekNotTextarea.className = 'form-control form-control-sm';
        ekNotTextarea.rows = 2;
        ekNotTextarea.value = hizmet.ekNot || '';
        ekNotTextarea.placeholder = 'Bu hizmetle ilgili ek notlar...';
        ekNotTextarea.addEventListener('input', (e) => hizmet.ekNot = e.target.value);
        ekNotInputCol.appendChild(ekNotTextarea);
        ekNotRow.append(ekNotLabelCol, ekNotInputCol);

        const ekstralarWrapper = document.createElement('div');
        ekstralarWrapper.className = 'ekstralar-wrapper mt-2';
        const ekstralarHeader = document.createElement('h6');
        ekstralarHeader.textContent = 'Ekstra Hizmetler/Masraflar:';
        ekstralarWrapper.appendChild(ekstralarHeader);
        
        const ekstralarContainer = document.createElement('div');
        ekstralarContainer.className = 'ekstralar-container';
        if (hizmet.ekstralar && hizmet.ekstralar.length > 0) {
            hizmet.ekstralar.forEach((ekstra, ekstraIndex) => {
                ekstralarContainer.appendChild(createExtraElement(ekstra, hizmet.id, ekstraIndex));
            });
        } else {
            ekstralarContainer.innerHTML = '<p class="text-muted small">Bu hizmet için henüz ekstra tanımlanmamış.</p>';
        }
        ekstralarWrapper.appendChild(ekstralarContainer);

        const yeniEkstraBtn = document.createElement('button');
        yeniEkstraBtn.className = 'btn btn-info btn-sm mt-1';
        yeniEkstraBtn.innerHTML = '<i class="fas fa-plus me-1"></i>Ekstra Ekle';
        yeniEkstraBtn.addEventListener('click', () => handleAddNewExtra(kategoriId, hizmetIndex, hizmet.id));
        ekstralarWrapper.appendChild(yeniEkstraBtn);
        
        const hizmetKontrolleri = document.createElement('div');
        hizmetKontrolleri.className = 'hizmet-kontrolleri text-end mt-2';
        const btnGroup = document.createElement('div');
        btnGroup.className = 'btn-group btn-group-sm';

        const parentCategory = kaplanDanismanlikTarifeData.kategoriler.find(k => k.id === kategoriId);
        const hizmetSayisi = parentCategory && parentCategory.hizmetler ? parentCategory.hizmetler.length : 0;

        const hizmetYukariBtn = createIconButton('fas fa-arrow-up', () => handleMoveService(kategoriId, hizmetIndex, -1), 'Yukarı Taşı', 'btn-outline-secondary', hizmetIndex === 0);
        const hizmetAsagiBtn = createIconButton('fas fa-arrow-down', () => handleMoveService(kategoriId, hizmetIndex, 1), 'Aşağı Taşı', 'btn-outline-secondary', hizmetIndex === hizmetSayisi - 1);
        const hizmetSilBtn = createIconButton('fas fa-trash-alt', () => handleDeleteService(kategoriId, hizmetIndex, hizmet.id), 'Hizmeti Sil', 'btn-outline-danger');
        
        btnGroup.append(hizmetYukariBtn, hizmetAsagiBtn, hizmetSilBtn);
        hizmetKontrolleri.appendChild(btnGroup);

        hizmetDiv.append(hizmetAdiRow, temelUcretRow, ekNotRow, ekstralarWrapper, hizmetKontrolleri);
        return hizmetDiv;
    }

    function createExtraElement(ekstra, hizmetId, ekstraIndex) {
        const ekstraDiv = document.createElement('div');
        ekstraDiv.className = 'tarife-ekstra-editor row gx-2 mb-1 align-items-center';
        ekstraDiv.dataset.ekstraId = ekstra.id;
        ekstraDiv.dataset.hizmetId = hizmetId;

        const aciklamaCol = document.createElement('div');
        aciklamaCol.className = 'col-md-6';
        const aciklamaInput = createTextInput(ekstra.aciklama || '', 'Ekstra açıklama (örn: Noter masrafı)', (val) => ekstra.aciklama = val);
        aciklamaCol.appendChild(aciklamaInput);

        const tutarCol = document.createElement('div');
        tutarCol.className = 'col-md-4';
        const tutarInput = createTextInput(ekstra.tutar || '', 'Tutar (örn: 500 TRY)', (val) => ekstra.tutar = val);
        tutarCol.appendChild(tutarInput);
        
        const silCol = document.createElement('div');
        silCol.className = 'col-md-2 text-end';
        const silBtn = createIconButton('fas fa-times', () => handleDeleteExtra(hizmetId, ekstraIndex, ekstra.id), 'Ekstrayı Sil', 'btn-danger btn-sm');
        silCol.appendChild(silBtn);

        ekstraDiv.append(aciklamaCol, tutarCol, silCol);
        return ekstraDiv;
    }

    function createIconButton(iconClass, onClick, title = '', btnClass = 'btn-secondary', disabled = false) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `btn ${btnClass} btn-sm`;
        btn.title = title;
        btn.innerHTML = `<i class="${iconClass}"></i>`;
        btn.disabled = disabled;
        btn.addEventListener('click', onClick);
        return btn;
    }
    
    function createLabelCol(text) {
        const col = document.createElement('div');
        col.className = 'col-md-3 col-form-label fw-semibold small';
        col.textContent = text;
        return col;
    }

    function createInputCol() {
        const col = document.createElement('div');
        col.className = 'col-md-9';
        return col;
    }

    function createTextInput(value, placeholder, onChangeCallback) {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control form-control-sm';
        input.value = value;
        input.placeholder = placeholder;
        input.addEventListener('input', (e) => onChangeCallback(e.target.value));
        return input;
    }

    async function handleSaveKaplanDanismanlikTarife() {
        if (!kaydetKaplanDanismanlikTarifeBtn) return;
        kaydetKaplanDanismanlikTarifeBtn.disabled = true;
        kaydetKaplanDanismanlikTarifeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Kaydediliyor...';

        console.log("Kaydedilecek Kaplan Danışmanlık Tarife Verisi:", JSON.parse(JSON.stringify(kaplanDanismanlikTarifeData)));

        try {
            const response = await fetch('/api/kaydet_kaplan_danismanlik_tarife', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': (typeof CSRF_TOKEN !== 'undefined' ? CSRF_TOKEN : '')
                },
                credentials: 'same-origin',
                body: JSON.stringify(kaplanDanismanlikTarifeData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showToast('Başarılı!', 'Kaplan Hukuk Danışmanlık tarifesi başarıyla kaydedildi.', 'success');
                isKaplanEditModeActive = false; 
                await fetchTarifeler(); // Sadece fetchTarifeler çağrılacak, o zaten UI'ı güncelleyecek.
            } else {
                showToast('Hata!', `Tarife kaydedilemedi: ${result.error || 'Bilinmeyen bir hata oluştu.'}`, 'danger');
            }
        } catch (error) {
            console.error('Tarife kaydetme hatası:', error);
            showToast('Hata!', 'Tarife kaydedilirken bir ağ hatası oluştu.', 'danger');
        } finally {
            kaydetKaplanDanismanlikTarifeBtn.disabled = false;
            kaydetKaplanDanismanlikTarifeBtn.innerHTML = '<i class="fas fa-save me-2"></i>Değişiklikleri Kaydet';
        }
    }
    
    // Event Listeners for Kaplan Section Buttons
    if (kaplanDuzenleBtn) {
        kaplanDuzenleBtn.addEventListener('click', () => {
            isKaplanEditModeActive = true; // Düzenleme moduna geç
            renderKaplanDanismanlikSection();
        });
    }

    if (kaplanIptalBtn) {
        kaplanIptalBtn.addEventListener('click', () => {
            isKaplanEditModeActive = false;
            // Son kaydedilen veriyi tekrar yüklemek için fetchTarifeler iyi bir seçenek
            // Bu, kullanıcı değişiklik yaptıysa ama kaydetmediyse, onları geri alır.
            fetchTarifeler(); // Bu renderKaplanDanismanlikSection'ı tetikleyecek ve doğru moda geçirecek
        });
    }

    if (kaydetKaplanDanismanlikTarifeBtn) {
        kaydetKaplanDanismanlikTarifeBtn.addEventListener('click', handleSaveKaplanDanismanlikTarife);
    }

    fetchTarifeler(); // Initial fetch
    
    const kaplanTabButton = document.getElementById('kaplan-danismanlik-tab');
    if(kaplanTabButton) {
        kaplanTabButton.addEventListener('shown.bs.tab', function (event) {
            // Sekme değiştiğinde, Kaplan bölümünün doğru modda (liste veya editör) render edilmesi için
            // fetchTarifeler() çağırılabilir veya doğrudan renderKaplanDanismanlikSection()
            // Eğer veri zaten güncelse ve sadece görünümü değiştirmek istiyorsak:
            renderKaplanDanismanlikSection();
        });
    }

    function handleAddNewExtra(kategoriId, hizmetIndex, hizmetId) {
        const kategori = kaplanDanismanlikTarifeData.kategoriler.find(k => k.id === kategoriId);
        if (!kategori || !kategori.hizmetler) {
            console.error("Ekstra eklenirken kategori bulunamadı veya kategoride hizmetler dizisi yok:", kategoriId);
            return;
        }
    
        const hizmet = kategori.hizmetler[hizmetIndex];
        if (!hizmet || hizmet.id !== hizmetId) {
            console.error("Ekstra eklenirken hizmet bulunamadı veya hizmet ID eşleşmedi:", kategoriId, hizmetIndex, hizmetId);
            if (!hizmet) return; 
        }
    
        if (!hizmet.ekstralar) {
            hizmet.ekstralar = [];
        }
    
        const newExtraId = 'ekstra_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const newExtra = {
            id: newExtraId,
            aciklama: '',
            tutar: '',
        };
        hizmet.ekstralar.push(newExtra);
        renderKaplanDanismanlikEditor();
    }

    function handleDeleteExtra(hizmetId, ekstraIndex, ekstraId) {
        let hizmetBulundu = null;
        // Kategori ve hizmeti bulmak için daha basit bir yol:
        const kategori = kaplanDanismanlikTarifeData.kategoriler.find(kat => 
            kat.hizmetler && kat.hizmetler.some(h => h.id === hizmetId)
        );
        if (kategori) {
            hizmetBulundu = kategori.hizmetler.find(h => h.id === hizmetId);
        }
    
        if (!hizmetBulundu || !hizmetBulundu.ekstralar) {
            console.error("Ekstra silinirken hizmet bulunamadı veya ekstralar dizisi yok:", hizmetId);
            return;
        }
    
        const ekstra = hizmetBulundu.ekstralar[ekstraIndex];
        if (!ekstra || ekstra.id !== ekstraId) {
            console.error("Ekstra silinirken ID eşleşmedi veya ekstra bulunamadı", hizmetId, ekstraIndex, ekstraId);
            if(!ekstra) return;
        }
        
        const ekstraAciklamasi = ekstra.aciklama || 'Bu ekstra';
        if (confirm(`"${ekstraAciklamasi}" ekstrasını silmek istediğinizden emin misiniz?`)) {
            hizmetBulundu.ekstralar.splice(ekstraIndex, 1);
            renderKaplanDanismanlikEditor();
        }
    }
}); 