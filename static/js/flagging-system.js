/* Flagging System JavaScript Component */

class FlaggingSystem {
    constructor() {
        this.isInitialized = false;
        this.init();
    }

    init() {
        if (this.isInitialized) return;
        
        // Add flag modal to body if it doesn't exist
        this.createFlagModal();
        
        // Bind event listeners
        this.bindEvents();
        
        this.isInitialized = true;
    }

    createFlagModal() {
        if (document.getElementById('flagModal')) return;
        
        const modalHTML = `
            <div class="modal fade" id="flagModal" tabindex="-1" role="dialog" aria-labelledby="flagModalLabel" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="flagModalLabel">
                                <i class="fas fa-flag text-warning"></i> Flag Content
                            </h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <form id="flagForm">
                                <input type="hidden" id="flagContentType" name="content_type">
                                <input type="hidden" id="flagObjectId" name="object_id">
                                
                                <div class="form-group">
                                    <label for="flagType">Why are you flagging this content?</label>
                                    <select class="form-control" id="flagType" name="flag_type" required>
                                        <option value="">-- Select a reason --</option>
                                        <option value="inappropriate">Inappropriate content</option>
                                        <option value="spam">Spam or advertising</option>
                                        <option value="misinformation">Misinformation or false data</option>
                                        <option value="copyright">Copyright violation</option>
                                        <option value="harassment">Harassment or abuse</option>
                                        <option value="duplicate">Duplicate content</option>
                                        <option value="off_topic">Off-topic or irrelevant</option>
                                        <option value="other">Other (explain below)</option>
                                    </select>
                                </div>
                                
                                <div class="form-group">
                                    <label for="flagDescription">Please provide details about the issue:</label>
                                    <textarea class="form-control" id="flagDescription" name="description" rows="4" 
                                              placeholder="Explain why this content should be reviewed..." required></textarea>
                                    <small class="form-text text-muted">
                                        Be specific about the issue to help moderators review it quickly.
                                    </small>
                                </div>
                                
                                <div class="form-group">
                                    <label for="flagPriority">Priority Level:</label>
                                    <select class="form-control" id="flagPriority" name="priority">
                                        <option value="low">Low - Minor issue</option>
                                        <option value="medium" selected>Medium - Moderate concern</option>
                                        <option value="high">High - Serious issue</option>
                                        <option value="critical">Critical - Urgent attention needed</option>
                                    </select>
                                </div>
                                
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle"></i>
                                    <strong>Community Guidelines:</strong> Flags are reviewed by our moderation team. 
                                    Please only flag content that genuinely violates our guidelines. 
                                    Misuse of the flagging system may result in restrictions on your account.
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-warning" id="submitFlag">
                                <i class="fas fa-flag"></i> Submit Flag
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    bindEvents() {
        // Handle flag button clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('.flag-content-btn, .flag-content-btn *')) {
                e.preventDefault();
                const button = e.target.closest('.flag-content-btn');
                this.showFlagModal(button);
            }
        });

        // Handle flag form submission
        const submitButton = document.getElementById('submitFlag');
        if (submitButton) {
            submitButton.addEventListener('click', () => this.submitFlag());
        }

        // Handle modal reset when closed
        $('#flagModal').on('hidden.bs.modal', () => {
            this.resetFlagForm();
        });
    }

    showFlagModal(button) {
        const contentType = button.dataset.contentType;
        const objectId = button.dataset.objectId;
        const contentDescription = button.dataset.contentDescription || 'this content';
        
        if (!contentType || !objectId) {
            this.showNotification('Error: Missing content information', 'error');
            return;
        }

        // Set form values
        document.getElementById('flagContentType').value = contentType;
        document.getElementById('flagObjectId').value = objectId;
        
        // Update modal title
        document.getElementById('flagModalLabel').innerHTML = 
            `<i class="fas fa-flag text-warning"></i> Flag ${contentDescription}`;
        
        // Show modal
        $('#flagModal').modal('show');
    }

    async submitFlag() {
        const form = document.getElementById('flagForm');
        const formData = new FormData(form);
        const submitButton = document.getElementById('submitFlag');
        
        // Validate form
        if (!this.validateFlagForm(form)) {
            return;
        }

        // Show loading state
        const originalText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        try {
            const response = await fetch('/ajax/flag-content/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                $('#flagModal').modal('hide');
                this.showNotification(data.message, 'success');
                
                // Update button to show it's been flagged
                this.updateFlaggedButton(formData.get('content_type'), formData.get('object_id'));
            } else {
                this.showNotification(data.error || 'Error submitting flag', 'error');
            }
        } catch (error) {
            console.error('Error submitting flag:', error);
            this.showNotification('Network error occurred', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }
    }

    validateFlagForm(form) {
        const flagType = form.querySelector('#flagType').value;
        const description = form.querySelector('#flagDescription').value.trim();

        if (!flagType) {
            this.showNotification('Please select a reason for flagging', 'error');
            return false;
        }

        if (!description || description.length < 10) {
            this.showNotification('Please provide at least 10 characters describing the issue', 'error');
            return false;
        }

        return true;
    }

    updateFlaggedButton(contentType, objectId) {
        const buttons = document.querySelectorAll(
            `.flag-content-btn[data-content-type="${contentType}"][data-object-id="${objectId}"]`
        );
        
        buttons.forEach(button => {
            button.classList.remove('btn-outline-warning');
            button.classList.add('btn-warning');
            button.innerHTML = '<i class="fas fa-flag"></i> Flagged';
            button.disabled = true;
            button.title = 'You have flagged this content';
        });
    }

    resetFlagForm() {
        const form = document.getElementById('flagForm');
        if (form) {
            form.reset();
            document.getElementById('flagContentType').value = '';
            document.getElementById('flagObjectId').value = '';
        }
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    // Static method to create flag button
    static createFlagButton(contentType, objectId, contentDescription = '', options = {}) {
        const {
            size = 'sm',
            text = 'Flag',
            className = 'btn-outline-warning',
            icon = 'fas fa-flag'
        } = options;

        return `
            <button type="button" 
                    class="btn btn-${size} ${className} flag-content-btn"
                    data-content-type="${contentType}"
                    data-object-id="${objectId}"
                    data-content-description="${contentDescription}"
                    title="Flag this content for review">
                <i class="${icon}"></i> ${text}
            </button>
        `;
    }
}

// Initialize flagging system when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.flaggingSystem = new FlaggingSystem();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlaggingSystem;
}
