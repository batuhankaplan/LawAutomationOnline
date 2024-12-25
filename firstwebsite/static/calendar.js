document.addEventListener('DOMContentLoaded', function() {
    const daysContainer = document.getElementById('days');
    const currentMonthElement = document.getElementById('currentMonth');
    const prevButton = document.getElementById('prevMonth');
    const nextButton = document.getElementById('nextMonth');

    let currentDate = new Date();
    let events = {};

    const aylar = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ];

    function renderCalendar(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        
        const firstDay = new Date(year, month, 1);
        let startingDay = firstDay.getDay() || 7;
        
        const lastDay = new Date(year, month + 1, 0);
        const totalDays = lastDay.getDate();

        currentMonthElement.textContent = `${aylar[month]} ${year}`;
        daysContainer.innerHTML = '';

        for (let i = 1; i < startingDay; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.className = 'day empty';
            daysContainer.appendChild(emptyDay);
        }

        for (let day = 1; day <= totalDays; day++) {
            const dayElement = document.createElement('div');
            dayElement.className = 'day';
            
            const dateKey = `${year}-${month+1}-${day}`;
            
            if (day === currentDate.getDate() && 
                month === currentDate.getMonth() && 
                year === currentDate.getFullYear()) {
                dayElement.classList.add('today');
            }

            const dayContent = document.createElement('div');
            dayContent.className = 'day-content';

            const dayNumber = document.createElement('div');
            dayNumber.className = 'day-number';
            dayNumber.textContent = day;

            const eventContent = document.createElement('div');
            eventContent.className = 'event-content';

            if (events[dateKey]) {
                const eventText = document.createElement('div');
                eventText.className = 'event-text';
                eventText.textContent = events[dateKey];
                eventText.onclick = function(e) {
                    e.stopPropagation();
                    showEventPreview(dateKey, events[dateKey]);
                };
                
                const editButton = document.createElement('button');
                editButton.className = 'edit-event-btn';
                editButton.innerHTML = '<i class="material-icons">edit</i>';
                editButton.title = 'Düzenle';
                editButton.onclick = function(e) {
                    e.stopPropagation();
                    showEventModal(dateKey, true);
                };
                
                eventContent.appendChild(eventText);
                eventContent.appendChild(editButton);
            }

            dayContent.appendChild(dayNumber);
            dayContent.appendChild(eventContent);

            const addButton = document.createElement('button');
            addButton.className = 'add-event-btn';
            addButton.innerHTML = '<i class="material-icons">add</i>';
            addButton.title = 'Yeni Not Ekle';
            addButton.onclick = function(e) {
                e.stopPropagation();
                showEventModal(dateKey, false);
            };

            dayElement.appendChild(dayContent);
            dayElement.appendChild(addButton);
            daysContainer.appendChild(dayElement);
        }
    }

    function showEventModal(dateKey, isEdit) {
        const existingModal = document.querySelector('.event-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.className = 'event-modal';
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${isEdit ? 'Notu Düzenle' : 'Yeni Not Ekle'}</h3>
                    <button class="close-modal">
                        <i class="material-icons">close</i>
                    </button>
                </div>
                <div class="modal-body">
                    <textarea placeholder="Notunuzu girin...">${isEdit ? events[dateKey] || '' : ''}</textarea>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-cancel">İptal</button>
                    <button class="btn modal-save">Kaydet</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        
        const closeBtn = modal.querySelector('.close-modal');
        const cancelBtn = modal.querySelector('.modal-cancel');
        const saveBtn = modal.querySelector('.modal-save');
        const textarea = modal.querySelector('textarea');

        closeBtn.onclick = cancelBtn.onclick = function() {
            modal.remove();
        };

        saveBtn.onclick = function() {
            events[dateKey] = textarea.value;
            renderCalendar(currentDate);
            modal.remove();
        };

        modal.onclick = function(e) {
            if (e.target === modal) {
                modal.remove();
            }
        };

        textarea.focus();
    }

    function showEventPreview(dateKey, eventText) {
        const existingModal = document.querySelector('.preview-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.className = 'preview-modal';
        
        modal.innerHTML = `
            <div class="preview-content">
                <div class="preview-header">
                    <h3>Not Detayı</h3>
                    <button class="close-modal">
                        <i class="material-icons">close</i>
                    </button>
                </div>
                <div class="preview-body">
                    <p>${eventText}</p>
                </div>
                <div class="preview-footer">
                    <button class="btn btn-secondary preview-close">Kapat</button>
                    <button class="btn preview-edit">Düzenle</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtn = modal.querySelector('.close-modal');
        const closeButton = modal.querySelector('.preview-close');
        const editButton = modal.querySelector('.preview-edit');

        closeBtn.onclick = closeButton.onclick = function() {
            modal.remove();
        };

        editButton.onclick = function() {
            modal.remove();
            showEventModal(dateKey, true);
        };

        modal.onclick = function(e) {
            if (e.target === modal) {
                modal.remove();
            }
        };
    }

    prevButton.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(currentDate);
    });

    nextButton.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(currentDate);
    });

    renderCalendar(currentDate);
});