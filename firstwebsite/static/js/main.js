// Dropdown menülerin otomatik kapanmasını engelle
$(document).on('click', '.dropdown-menu', function (e) {
    e.stopPropagation();
});

// Toastr bildirim ayarları
toastr.options = {
    "closeButton": true,
    "debug": false,
    "newestOnTop": true,
    "progressBar": true,
    "positionClass": "toast-top-right",
    "preventDuplicates": false,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "5000",
    "extendedTimeOut": "1000",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
};

// Form doğrulama fonksiyonu
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// AJAX hata işleme
function handleAjaxError(xhr, status, error) {
    console.error('AJAX Error:', status, error);
    let errorMessage = 'Bir hata oluştu';
    
    if (xhr.responseJSON && xhr.responseJSON.message) {
        errorMessage = xhr.responseJSON.message;
    }
    
    toastr.error(errorMessage);
}

// Sayfa yüklendiğinde çalışacak kodlar
$(document).ready(function() {
    // Bootstrap tooltip'lerini aktifleştir
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Form submit olaylarını yakala
    $('form').on('submit', function(e) {
        if (!validateForm(this.id)) {
            e.preventDefault();
            toastr.warning('Lütfen tüm gerekli alanları doldurun');
        }
    });
}); 