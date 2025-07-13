/**
 * Universal Tutorial System for Council Finance Counters
 * 
 * This JavaScript class provides a consistent tutorial experience
 * across the entire application. It integrates with the Django
 * tutorial engine and supports debug mode, A/B testing, and
 * extensible configuration.
 */

class UniversalTutorial {
  constructor(config) {
    this.config = {
      tutorialId: 'default',
      debugMode: false,
      storageKey: 'seen_default',
      slides: [],
      title: 'Tutorial',
      animationDuration: 300,
      backdropDismissible: true,
      escapeDismissible: true,
      ...config
    };
    
    this.currentSlide = 0;
    this.modal = null;
    this.content = null;
    this.currentSpan = null;
    this.totalSpan = null;
    this.prevBtn = null;
    this.nextBtn = null;
    this.skipBtn = null;
    
    this.createModal();
    this.init();
  }
  
  createModal() {
    // Create modal HTML dynamically to avoid template conflicts
    const modalHTML = `
      <div id="tutorial-modal-${this.config.tutorialId}" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center tutorial-modal">
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 transform transition-all">
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900">${this.config.title}</h3>
              <div class="text-sm text-gray-500">
                <span class="tutorial-current">1</span> of <span class="tutorial-total">1</span>
              </div>
            </div>
            
            <div class="tutorial-content">
              <!-- Tutorial slides will be dynamically inserted here -->
            </div>
            
            <div class="flex justify-between items-center mt-6">
              <button class="tutorial-prev px-4 py-2 text-gray-600 hover:text-gray-800 hidden">
                ← Previous
              </button>
              <div class="flex gap-2">
                ${this.config.debugMode ? '<button class="tutorial-reset px-2 py-1 text-xs text-red-600 hover:text-red-800 border border-red-300 rounded">Reset All</button>' : ''}
                <button class="tutorial-skip px-4 py-2 text-gray-600 hover:text-gray-800">
                  Skip
                </button>
                <button class="tutorial-next px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                  Got it
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Insert modal into document
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Get references to modal elements
    this.modal = document.getElementById(`tutorial-modal-${this.config.tutorialId}`);
    this.content = this.modal.querySelector('.tutorial-content');
    this.currentSpan = this.modal.querySelector('.tutorial-current');
    this.totalSpan = this.modal.querySelector('.tutorial-total');
    this.prevBtn = this.modal.querySelector('.tutorial-prev');
    this.nextBtn = this.modal.querySelector('.tutorial-next');
    this.skipBtn = this.modal.querySelector('.tutorial-skip');
    this.resetBtn = this.modal.querySelector('.tutorial-reset');
  }
  
  init() {
    if (!this.config.slides.length) {
      console.warn(`No slides configured for tutorial: ${this.config.tutorialId}`);
      return;
    }
    
    this.totalSpan.textContent = this.config.slides.length;
    this.setupEventListeners();
    this.updateSlide();
    
    // Show tutorial based on engine logic
    if (this.shouldShow()) {
      // Small delay to ensure page is fully loaded
      setTimeout(() => this.show(), 500);
    }
  }
  
  shouldShow() {
    // Always show in debug mode
    if (this.config.debugMode) {
      return true;
    }
    
    // Check localStorage
    return !localStorage.getItem(this.config.storageKey);
  }
  
  setupEventListeners() {
    this.nextBtn.addEventListener('click', () => this.next());
    this.prevBtn.addEventListener('click', () => this.previous());
    this.skipBtn.addEventListener('click', () => this.close());
    
    if (this.resetBtn) {
      this.resetBtn.addEventListener('click', () => this.resetAllTutorials());
    }
    
    // Close on outside click (if enabled)
    if (this.config.backdropDismissible) {
      this.modal.addEventListener('click', (e) => {
        if (e.target === this.modal) {
          this.close();
        }
      });
    }
    
    // Close on Escape key (if enabled)
    if (this.config.escapeDismissible) {
      this.escapeHandler = (e) => {
        if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
          this.close();
        }
      };
      document.addEventListener('keydown', this.escapeHandler);
    }
  }
  
  updateSlide() {
    const slide = this.config.slides[this.currentSlide];
    this.content.innerHTML = `
      <div class="text-gray-700 leading-relaxed">
        ${slide.content}
      </div>
    `;
    
    this.currentSpan.textContent = this.currentSlide + 1;
    
    // Update button states
    this.prevBtn.classList.toggle('hidden', this.currentSlide === 0);
    
    if (this.currentSlide === this.config.slides.length - 1) {
      this.nextBtn.textContent = 'Got it';
    } else {
      this.nextBtn.textContent = 'Next →';
    }
  }
  
  next() {
    if (this.currentSlide < this.config.slides.length - 1) {
      this.currentSlide++;
      this.updateSlide();
    } else {
      this.close();
    }
  }
  
  previous() {
    if (this.currentSlide > 0) {
      this.currentSlide--;
      this.updateSlide();
    }
  }
  
  show() {
    this.modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Track tutorial display (for analytics)
    this.trackEvent('tutorial_shown');
  }
  
  close() {
    this.modal.classList.add('hidden');
    document.body.style.overflow = '';
    
    // Only mark as seen if not in debug mode
    if (!this.config.debugMode) {
      localStorage.setItem(this.config.storageKey, '1');
    }
    
    // Clean up event listeners
    if (this.escapeHandler) {
      document.removeEventListener('keydown', this.escapeHandler);
    }
    
    // Track tutorial completion
    this.trackEvent('tutorial_completed');
  }
  
  resetAllTutorials() {
    // Remove all tutorial-related localStorage items
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith('seen_')) {
        localStorage.removeItem(key);
      }
    });
    
    console.log('All tutorials reset. Refresh the page to see them again.');
    this.trackEvent('tutorials_reset');
  }
  
  trackEvent(eventName) {
    // Future: Send to analytics service
    if (this.config.debugMode) {
      console.log(`Tutorial Event: ${eventName} for ${this.config.tutorialId}`);
    }
  }
  
  // Static method to create tutorial from Django config
  static fromDjangoConfig(djangoConfig) {
    return new UniversalTutorial(djangoConfig);
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = UniversalTutorial;
}

// Also make available globally
window.UniversalTutorial = UniversalTutorial;
