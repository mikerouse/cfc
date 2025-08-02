/**
 * Following Page JavaScript
 * Handles comment forms, sharing functionality, and feed interactions
 */

class FollowingPage {
    constructor() {
        console.log('FollowingPage: Initializing...');
        this.init();
    }

    init() {
        this.bindCommentButtons();
        this.bindShareButtons();
        this.addSmoothScrolling();
        this.addLoadingStates();
        console.log('FollowingPage: Initialization complete');
    }

    /**
     * Bind comment button functionality
     */
    bindCommentButtons() {
        const commentButtons = document.querySelectorAll('[data-action="show-comments"]');
        console.log(`FollowingPage: Found ${commentButtons.length} comment buttons`);
        
        commentButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const updateId = button.dataset.updateId;
                this.toggleCommentForm(updateId);
            });
        });
    }

    /**
     * Toggle comment form visibility
     */
    toggleCommentForm(updateId) {
        const commentSection = document.getElementById(`comments-${updateId}`);
        
        if (!commentSection) {
            // Create comment section if it doesn't exist
            this.createCommentSection(updateId);
        } else {
            // Toggle existing section
            if (commentSection.classList.contains('hidden')) {
                commentSection.classList.remove('hidden');
                commentSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                commentSection.classList.add('hidden');
            }
        }
    }

    /**
     * Create comment section dynamically
     */
    createCommentSection(updateId) {
        const updateCard = document.querySelector(`[data-update-id="${updateId}"]`);
        if (!updateCard) return;

        const commentSection = document.createElement('div');
        commentSection.id = `comments-${updateId}`;
        commentSection.className = 'mt-4 border-t border-gray-100 pt-4';
        commentSection.innerHTML = `
            <div class="space-y-4">
                <!-- Comment Form -->
                <div class="bg-gray-50 rounded-lg p-4">
                    <form class="space-y-3" data-comment-form="${updateId}">
                        <textarea 
                            placeholder="Add a comment..." 
                            class="w-full p-3 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows="3"></textarea>
                        <div class="flex justify-between items-center">
                            <div class="text-xs text-gray-500">
                                Be respectful and constructive in your comments
                            </div>
                            <div class="flex gap-2">
                                <button type="button" 
                                        class="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                                        onclick="this.closest('.space-y-4').parentElement.classList.add('hidden')">
                                    Cancel
                                </button>
                                <button type="submit" 
                                        class="px-4 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors">
                                    Comment
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
                
                <!-- Existing Comments -->
                <div class="space-y-3" id="comments-list-${updateId}">
                    <div class="text-sm text-gray-500 text-center py-4">
                        No comments yet. Be the first to comment!
                    </div>
                </div>
            </div>
        `;

        // Insert after the actions div
        const actionsDiv = updateCard.querySelector('.flex.items-center.justify-between.pt-4');
        if (actionsDiv && actionsDiv.parentElement) {
            actionsDiv.parentElement.insertBefore(commentSection, actionsDiv.nextSibling);
        }

        // Scroll to the new form
        commentSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Bind form submission
        this.bindCommentForm(updateId);
    }

    /**
     * Bind comment form submission
     */
    bindCommentForm(updateId) {
        const form = document.querySelector(`[data-comment-form="${updateId}"]`);
        if (!form) return;

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const textarea = form.querySelector('textarea');
            const comment = textarea.value.trim();
            
            if (!comment) return;

            // Show loading state
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Posting...';
            submitButton.disabled = true;

            // Simulate API call (replace with actual implementation)
            setTimeout(() => {
                this.addComment(updateId, comment);
                textarea.value = '';
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }, 1000);
        });
    }

    /**
     * Add comment to the list
     */
    addComment(updateId, comment) {
        const commentsList = document.getElementById(`comments-list-${updateId}`);
        if (!commentsList) return;

        // Remove "no comments" message if present
        const noCommentsMsg = commentsList.querySelector('.text-center');
        if (noCommentsMsg) {
            noCommentsMsg.remove();
        }

        const commentElement = document.createElement('div');
        commentElement.className = 'flex gap-3 p-3 bg-white rounded-lg border border-gray-100';
        commentElement.innerHTML = `
            <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                U
            </div>
            <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                    <span class="font-medium text-gray-900">You</span>
                    <span class="text-xs text-gray-500">just now</span>
                </div>
                <p class="text-gray-700 text-sm">${comment}</p>
            </div>
        `;

        commentsList.appendChild(commentElement);
        
        // Update comment count
        const commentButton = document.querySelector(`[data-update-id="${updateId}"] [data-action="show-comments"] span`);
        if (commentButton) {
            const currentCount = parseInt(commentButton.textContent) || 0;
            commentButton.textContent = currentCount + 1;
        }
    }

    /**
     * Bind share button functionality
     */
    bindShareButtons() {
        const shareButtons = document.querySelectorAll('[data-action="share"]');
        console.log(`FollowingPage: Found ${shareButtons.length} share buttons`);
        
        shareButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const updateId = button.dataset.updateId;
                this.showShareModal(updateId);
            });
        });
    }

    /**
     * Show share modal with social media options
     */
    showShareModal(updateId) {
        const updateCard = document.querySelector(`[data-update-id="${updateId}"]`);
        if (!updateCard) return;

        // Get update details for sharing
        const councilNameElement = updateCard.querySelector('h3');
        const updateTextElement = updateCard.querySelector('.text-gray-900.leading-relaxed');
        
        if (!councilNameElement || !updateTextElement) return;
        
        const councilName = councilNameElement.textContent;
        const updateText = updateTextElement.textContent;
        
        const shareUrl = window.location.href;
        const shareText = `${councilName}: ${updateText.substring(0, 100)}...`;

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.id = 'share-modal';
        modal.innerHTML = `
            <div class="bg-white rounded-xl max-w-md w-full mx-4 p-6">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-gray-900">Share Update</h3>
                    <button class="text-gray-400 hover:text-gray-600" data-action="close-modal">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                
                <div class="space-y-3">
                    <button data-share="twitter" 
                            class="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                        <div class="w-8 h-8 bg-black rounded flex items-center justify-center">
                            <span class="text-white font-bold text-sm">𝕏</span>
                        </div>
                        <span class="font-medium text-gray-900">Share on X (Twitter)</span>
                    </button>
                    
                    <button data-share="facebook" 
                            class="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                        <div class="w-8 h-8 bg-blue-600 rounded flex items-center justify-center">
                            <span class="text-white font-bold text-sm">f</span>
                        </div>
                        <span class="font-medium text-gray-900">Share on Facebook</span>
                    </button>
                    
                    <button data-share="whatsapp" 
                            class="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                        <div class="w-8 h-8 bg-green-500 rounded flex items-center justify-center">
                            <span class="text-white font-bold text-sm">W</span>
                        </div>
                        <span class="font-medium text-gray-900">Share on WhatsApp</span>
                    </button>
                    
                    <button data-share="copy" 
                            class="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                        <div class="w-8 h-8 bg-gray-600 rounded flex items-center justify-center">
                            <span class="text-white font-bold text-sm">🔗</span>
                        </div>
                        <span class="font-medium text-gray-900">Copy Link</span>
                    </button>
                </div>
                
                <button data-action="close-modal" 
                        class="w-full mt-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
                    Cancel
                </button>
            </div>
        `;

        document.body.appendChild(modal);

        // Set up event handlers
        modal.addEventListener('click', (e) => {
            // Close on backdrop click
            if (e.target === modal) {
                modal.remove();
            }
            
            // Handle button clicks
            const button = e.target.closest('button');
            if (!button) return;
            
            if (button.dataset.action === 'close-modal') {
                modal.remove();
                return;
            }
            
            if (button.dataset.share) {
                this.handleShare(button.dataset.share, shareText, shareUrl, button);
            }
        });
    }
    
    /**
     * Handle share actions
     */
    handleShare(platform, text, url, button) {
        const encodedText = encodeURIComponent(text);
        const encodedUrl = encodeURIComponent(url);
        
        switch(platform) {
            case 'twitter':
                window.open(`https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`, '_blank');
                break;
                
            case 'facebook':
                window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`, '_blank');
                break;
                
            case 'whatsapp':
                window.open(`https://wa.me/?text=${encodedText}%20${encodedUrl}`, '_blank');
                break;
                
            case 'copy':
                navigator.clipboard.writeText(url).then(() => {
                    const originalContent = button.innerHTML;
                    button.innerHTML = '<span class="text-green-600">✓ Copied!</span>';
                    setTimeout(() => {
                        button.innerHTML = originalContent;
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                });
                break;
        }
    }

    /**
     * Add smooth scrolling for internal links
     */
    addSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    /**
     * Add loading states for buttons
     */
    addLoadingStates() {
        document.querySelectorAll('button').forEach(button => {
            if (button.classList.contains('load-more')) {
                button.addEventListener('click', function() {
                    this.innerHTML = 'Loading...';
                    this.disabled = true;
                });
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new FollowingPage();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FollowingPage;
}