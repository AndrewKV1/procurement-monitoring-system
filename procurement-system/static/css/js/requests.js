class RequestManager {
    constructor() {
        this.supplierData = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.calculateTotal();
        this.updateApprovalInfo();
    }

    bindEvents() {
     
        document.getElementById('quantity').addEventListener('input', () => this.calculateTotal());
        document.getElementById('unit_price').addEventListener('input', () => this.calculateTotal());
        
 
        document.getElementById('supplier_id').addEventListener('change', (e) => {
            this.updateSupplierInfo(e.target.value);
            this.updateApprovalInfo();
        });

        document.getElementById('saveDraft').addEventListener('click', () => {
            this.saveDraft();
        });

 
        document.querySelector('.request-form').addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
            }
        });
    }

    calculateTotal() {
        const quantity = parseInt(document.getElementById('quantity').value) || 0;
        const unitPrice = parseFloat(document.getElementById('unit_price').value) || 0;
        const totalAmount = quantity * unitPrice;

        document.getElementById('total_amount').value = this.formatCurrency(totalAmount);
        this.updateApprovalInfo();
    }

    updateSupplierInfo(supplierId) {
        const select = document.getElementById('supplier_id');
        const selectedOption = select.options[select.selectedIndex];
        const rating = selectedOption?.dataset.rating || '0';
        
        document.getElementById('supplierRating').textContent = rating;
        
   
        if (parseFloat(rating) < 4.2) {
            this.showRatingWarning(rating);
        } else {
            this.hideRatingWarning();
        }
    }

    updateApprovalInfo() {
        const totalAmount = this.getTotalAmount();
        const approvalElement = document.getElementById('auto_approval');
        const infoElement = document.getElementById('approvalInfo');
        const flowElement = document.getElementById('approvalFlow');

        let status = 'Очікує затвердження';
        let statusClass = 'pending';
        let approvalSteps = [];


        if (totalAmount <= 25000) {
            status = 'Автоматично затверджено';
            statusClass = 'approved';
            infoElement.textContent = 'Сума менше 25,000 грн - автоматичне затвердження';
        } 
       
        else if (totalAmount > 100000) {
            status = 'Потребує затвердження';
            statusClass = 'pending';
            infoElement.textContent = 'Сума понад 100,000 грн - необхідно затвердження фінансовим директором';
            approvalSteps = [
                { name: 'Керівник проекту', required: true },
                { name: 'Фінансовий директор', required: true }
            ];
        }

        else if (totalAmount > 25000) {
            status = 'Потребує затвердження';
            statusClass = 'pending';
            infoElement.textContent = 'Сума понад 25,000 грн - необхідно затвердження керівником проекту';
            approvalSteps = [
                { name: 'Керівник проекту', required: true }
            ];
        }

        approvalElement.value = status;
        approvalElement.className = `readonly-field status-${statusClass}`;

     
        this.renderApprovalFlow(flowElement, approvalSteps);
    }

    renderApprovalFlow(container, steps) {
        if (steps.length === 0) {
            container.innerHTML = '<p>Автоматичне затвердження - додаткові кроки не потрібні</p>';
            return;
        }

        container.innerHTML = steps.map(step => `
            <div class="approval-step ${step.required ? 'required' : ''}">
                <div style="font-weight: 600; margin-bottom: 5px;">${step.name}</div>
                <div style="font-size: 0.875rem; color: #666;">
                    ${step.required ? 'Обов\'язкове затвердження' : 'Рекомендоване затвердження'}
                </div>
                <div style="margin-top: 10px;">
                    ${step.required ? ' Очікує' : ' Рекомендація'}
                </div>
            </div>
        `).join('');
    }

    validateForm() {
        const totalAmount = this.getTotalAmount();
        const justification = document.getElementById('justification').value;
        const supplierRating = parseFloat(document.getElementById('supplierRating').textContent);


        if (totalAmount > 50000 && justification.trim().length < 50) {
            alert('Для закупівель понад 50,000 грн необхідно надати детальне обґрунтування вибору постачальника (мінімум 50 символів)');
            return false;
        }


        if (supplierRating < 4.2) {
            const confirmed = confirm(
                `Увага! Рейтинг обраного постачальника (${supplierRating}) нижче рекомендованого мінімуму (4.2).\n\n` +
                `Бажаєте продовжити?`
            );
            if (!confirmed) {
                return false;
            }
        }

        return true;
    }

    saveDraft() {
        const formData = new FormData(document.querySelector('.request-form'));
        const draftData = {};
        
        for (let [key, value] of formData.entries()) {
            draftData[key] = value;
        }

        localStorage.setItem('purchaseRequestDraft', JSON.stringify(draftData));
        
        alert('Чернетку заявки збережено! Ви можете продовжити заповнення пізніше.');
    }

    loadDraft() {
        const draftData = localStorage.getItem('purchaseRequestDraft');
        if (draftData) {
            const data = JSON.parse(draftData);
            
            Object.keys(data).forEach(key => {
                const element = document.querySelector(`[name="${key}"]`);
                if (element) {
                    element.value = data[key];
                }
            });
            
            this.calculateTotal();
            this.updateApprovalInfo();
            
            alert('Чернетку заявки завантажено!');
        }
    }

    getTotalAmount() {
        const quantity = parseInt(document.getElementById('quantity').value) || 0;
        const unitPrice = parseFloat(document.getElementById('unit_price').value) || 0;
        return quantity * unitPrice;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('uk-UA', {
            style: 'currency',
            currency: 'UAH'
        }).format(amount);
    }

    showRatingWarning(rating) {
        let warningElement = document.getElementById('ratingWarning');
        
        if (!warningElement) {
            warningElement = document.createElement('div');
            warningElement.id = 'ratingWarning';
            warningElement.className = 'alert alert-warning';
            document.querySelector('.form-section').appendChild(warningElement);
        }
        
        warningElement.innerHTML = `
             <strong>Увага!</strong> Рейтинг постачальника (${rating}) нижче рекомендованого мінімуму (4.2). 
            <br>Рекомендується розглянути альтернативних постачальників.
        `;
    }

    hideRatingWarning() {
        const warningElement = document.getElementById('ratingWarning');
        if (warningElement) {
            warningElement.remove();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const requestManager = new RequestManager();
    

    const urlParams = new URLSearchParams(window.location.search);
    const supplierId = urlParams.get('supplier_id');
    
    if (supplierId) {
        document.getElementById('supplier_id').value = supplierId;
        requestManager.updateSupplierInfo(supplierId);
        requestManager.updateApprovalInfo();
    }
    
    const loadDraftBtn = document.createElement('button');
    loadDraftBtn.type = 'button';
    loadDraftBtn.className = 'btn btn-info';
    loadDraftBtn.textContent = ' Завантажити чернетку';
    loadDraftBtn.onclick = () => requestManager.loadDraft();
    
    document.querySelector('.form-actions').prepend(loadDraftBtn);
});