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
            
            if (day === currentDate.getDate() && 
                month === currentDate.getMonth() && 
                year === currentDate.getFullYear()) {
                dayElement.classList.add('today');
            }

            const dateKey = `${year}-${month+1}-${day}`;
            
            dayElement.innerHTML = `
                <div class="day-number">${day}</div>
                <div class="add-event">+</div>
                ${events[dateKey] ? `<div class="event-text">${events[dateKey]}</div>` : ''}
            `;
            
            dayElement.querySelector('.add-event').addEventListener('click', function(e) {
                e.stopPropagation();
                showEventModal(dateKey);
            });

            daysContainer.appendChild(dayElement);
        }
    }

    function showEventModal(dateKey) {
        const modal = document.createElement('div');
        modal.className = 'event-modal';
        modal.style.display = 'flex';
        
        modal.innerHTML = `
            <div class="modal-content">
                <textarea placeholder="Notunuzu girin...">${events[dateKey] || ''}</textarea>
                <button onclick="saveEvent('${dateKey}')">Kaydet</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    window.saveEvent = function(dateKey) {
        const modal = document.querySelector('.event-modal');
        const textarea = modal.querySelector('textarea');
        events[dateKey] = textarea.value;
        renderCalendar(currentDate);
        modal.remove();
    };

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