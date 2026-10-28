// Мобільна оптимізація
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== МОБІЛЬНА ОПТИМІЗАЦІЯ АКТИВОВАНА ===');

    // Елементи мобільної навігації
    const mobileNavToggle = document.getElementById('mobileNavToggle');
    const mainNav = document.getElementById('mainNav');
    const body = document.body;

    // Ініціалізація мобільної навігації
    initMobileNavigation();
    
    // Оптимізація таблиць для мобільних
    optimizeTablesForMobile();
    
    // Оптимізація форм для мобільних
    optimizeFormsForMobile();
    
    // Обробка сповіщень
    initMobileAlerts();
    
    // Touch оптимізація
    initTouchOptimization();
    
    // Запобігання масштабуванню
    preventZoomOnFocus();

    // ===== МОБІЛЬНА НАВІГАЦІЯ =====
    function initMobileNavigation() {
        if (!mobileNavToggle || !mainNav) return;

        mobileNavToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            mainNav.classList.toggle('active');
            mobileNavToggle.classList.toggle('active');
            body.style.overflow = mainNav.classList.contains('active') ? 'hidden' : '';
        });

        // Закриття меню при кліку поза ним
        document.addEventListener('click', function(e) {
            if (mainNav.classList.contains('active') && 
                !mainNav.contains(e.target) && 
                !mobileNavToggle.contains(e.target)) {
                closeMobileMenu();
            }
        });

        // Закриття меню при кліку на посилання
        mainNav.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                setTimeout(closeMobileMenu, 300);
            }
        });

        // Обробка клавіші ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeMobileMenu();
            }
        });
    }

    function closeMobileMenu() {
        mainNav.classList.remove('active');
        mobileNavToggle.classList.remove('active');
        body.style.overflow = '';
    }

    // ===== ОПТИМІЗАЦІЯ ТАБЛИЦЬ =====
    function optimizeTablesForMobile() {
        const tables = document.querySelectorAll('.table-responsive');
        
        tables.forEach(table => {
            if (isMobileDevice()) {
                table.classList.add('mobile-optimized');
                
                // Додаємо можливість гортання
                table.style.webkitOverflowScrolling = 'touch';
                
                // Оптимізація широких таблиць
                const wideTables = table.querySelectorAll('table');
                wideTables.forEach(wideTable => {
                    if (wideTable.offsetWidth > table.offsetWidth) {
                        wideTable.style.minWidth = '100%';
                    }
                });
            }
        });

        // Адаптація заголовків таблиць
        adaptTableHeaders();
    }

    function adaptTableHeaders() {
        const tables = document.querySelectorAll('.data-table');
        
        tables.forEach(table => {
            const headers = table.querySelectorAll('th');
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (headers[index] && isMobileDevice()) {
                        cell.setAttribute('data-label', headers[index].textContent.trim());
                    }
                });
            });
        });
    }

    // ===== ОПТИМІЗАЦІЯ ФОРМ =====
    function optimizeFormsForMobile() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            // Запобігання відправці форми при швидкому тапу
            let lastSubmitTime = 0;
            form.addEventListener('submit', function(e) {
                const now = Date.now();
                if (now - lastSubmitTime < 1000) {
                    e.preventDefault();
                    showMobileMessage('Будь ласка, зачекайте перед повторною відправкою', 'warning');
                }
                lastSubmitTime = now;
            });

            // Оптимізація полів вводу
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('focus', function() {
                    this.style.fontSize = '16px'; // Запобігає масштабуванню в iOS
                });
                
                // Валідація для мобільних
                input.addEventListener('blur', function() {
                    validateMobileInput(this);
                });
            });
        });
    }

    function validateMobileInput(input) {
        if (input.type === 'email' && input.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value)) {
                showInputError(input, 'Будь ласка, введіть коректний email');
                return false;
            }
        }
        
        if (input.hasAttribute('required') && !input.value.trim()) {
            showInputError(input, 'Це поле обов\'язкове для заповнення');
            return false;
        }
        
        clearInputError(input);
        return true;
    }

    function showInputError(input, message) {
        clearInputError(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mobile-input-error';
        errorDiv.style.cssText = `
            color: #e74c3c;
            font-size: 12px;
            margin-top: 5px;
            padding: 5px;
            background: #fdf2f2;
            border-radius: 4px;
            border-left: 3px solid #e74c3c;
        `;
        errorDiv.textContent = message;
        
        input.parentNode.appendChild(errorDiv);
        input.style.borderColor = '#e74c3c';
    }

    function clearInputError(input) {
        const existingError = input.parentNode.querySelector('.mobile-input-error');
        if (existingError) {
            existingError.remove();
        }
        input.style.borderColor = '';
    }

    // ===== МОБІЛЬНІ СПОВІЩЕННЯ =====
    function initMobileAlerts() {
        const alerts = document.querySelectorAll('.alert');
        
        alerts.forEach(alert => {
            // Автоматичне приховування
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.3s ease';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }, 5000);

            // Можливість закриття
            if (!alert.querySelector('.close-alert')) {
                const closeBtn = document.createElement('button');
                closeBtn.className = 'close-alert';
                closeBtn.innerHTML = '&times;';
                closeBtn.style.cssText = `
                    background: none;
                    border: none;
                    font-size: 1.2rem;
                    cursor: pointer;
                    padding: 0;
                    margin-left: auto;
                    min-width: 30px;
                    min-height: 30px;
                `;
                closeBtn.addEventListener('click', function() {
                    alert.remove();
                });
                
                alert.style.display = 'flex';
                alert.style.alignItems = 'center';
                alert.style.justifyContent = 'space-between';
                alert.appendChild(closeBtn);
            }
        });
    }

    // ===== TOACH ОПТИМІЗАЦІЯ =====
    function initTouchOptimization() {
        // Покращення відчуття від тапів
        const interactiveElements = document.querySelectorAll('a, button, .btn, [onclick]');
        
        interactiveElements.forEach(element => {
            element.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            });
            
            element.addEventListener('touchend', function() {
                this.style.transform = '';
            });
            
            element.addEventListener('touchcancel', function() {
                this.style.transform = '';
            });
        });

        // Запобігання виділенню тексту при тапах
        document.addEventListener('touchstart', function(e) {
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
            }
        }, { passive: false });
    }

    // ===== ЗАПОБІГАННЯ МАСШТАБУВАННЮ =====
    function preventZoomOnFocus() {
        let lastZoom = window.visualViewport ? window.visualViewport.scale : 1;
        
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', function() {
                if (this.scale !== lastZoom) {
                    document.activeElement.blur();
                    lastZoom = this.scale;
                }
            });
        }

        // Фокус на полях вводу
        document.addEventListener('focusin', function(e) {
            if (e.target.matches('input, select, textarea')) {
                setTimeout(() => {
                    if (window.visualViewport) {
                        window.scrollTo(0, 0);
                    }
                }, 100);
            }
        });
    }

    // ===== ДОДАТКОВІ ФУНКЦІЇ =====
    function isMobileDevice() {
        return window.innerWidth <= 768 || 
               /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    function showMobileMessage(message, type = 'info') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `mobile-message alert-${type}`;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'error' ? '#e74c3c' : type === 'success' ? '#27ae60' : '#3498db'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            font-size: 14px;
            max-width: 90%;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.style.opacity = '0';
            messageDiv.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
            }, 300);
        }, 3000);
    }

    // Обробка зміни орієнтації
    window.addEventListener('orientationchange', function() {
        setTimeout(() => {
            window.scrollTo(0, 0);
            optimizeTablesForMobile();
        }, 300);
    });

    // Обробка зміни розміру вікна
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            optimizeTablesForMobile();
            adaptTableHeaders();
        }, 250);
    });

    // Підтвердження для небезпечних дій
    const dangerousLinks = document.querySelectorAll('a[data-confirm]');
    dangerousLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    console.log('=== МОБІЛЬНА ОПТИМІЗАЦІЯ ЗАВЕРШЕНА ===');
});

// Додаткові утиліти для мобільних пристроїв
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Можливість додати PWA функціонал в майбутньому
        console.log('Service Worker підтримується');
    });
}

// Поліфіли для старих мобільних браузерів
if (!Element.prototype.matches) {
    Element.prototype.matches = Element.prototype.msMatchesSelector || 
                                Element.prototype.webkitMatchesSelector;
}

if (!Element.prototype.closest) {
    Element.prototype.closest = function(s) {
        var el = this;
        if (!document.documentElement.contains(el)) return null;
        do {
            if (el.matches(s)) return el;
            el = el.parentElement || el.parentNode;
        } while (el !== null && el.nodeType === 1);
        return null;
    };
}