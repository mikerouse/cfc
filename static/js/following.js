/**
 * Following Page JavaScript
 * Handles comment forms, sharing functionality, and feed interactions
 */

class FollowingPage {
    constructor() {
        console.log('FollowingPage: Initializing...');
        this.isAuthenticated = this.checkAuthentication();
        this.init();
    }

    init() {
        this.bindCommentButtons();
        this.bindShareButtons();
        this.bindLikeButtons();
        this.addSmoothScrolling();
        this.addLoadingStates();
        console.log('FollowingPage: Initialization complete');
    }

    checkAuthentication() {
        // Use Django-provided authentication status if available
        if (window.djangoContext && typeof window.djangoContext.isAuthenticated === 'boolean') {
            return window.djangoContext.isAuthenticated;
        }
        
        // Fallback: Check if user is authenticated by looking for authenticated user indicators
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        const logoutLink = document.querySelector('a[href*="logout"]');
        const userDropdown = document.querySelector('.user-dropdown, [data-dropdown="user"]');
        const authUserElement = document.querySelector('.auth-user, .user-info');
        
        // If we have CSRF token and logout link, user is likely authenticated
        return !!(csrfToken && csrfToken.value && logoutLink) || 
               !!(userDropdown || authUserElement);
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
                
                // Check authentication
                if (!this.isAuthenticated) {
                    this.showLoginPrompt('comment on updates');
                    return;
                }
                
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
            // Load existing comments
            this.loadComments(updateId);
        } else {
            // Toggle existing section
            if (commentSection.classList.contains('hidden')) {
                commentSection.classList.remove('hidden');
                commentSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                // Refresh comments when showing
                this.loadComments(updateId);
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

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const textarea = form.querySelector('textarea');
            const comment = textarea.value.trim();
            
            if (!comment) return;

            // Show loading state
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = 'Posting...';
            submitButton.disabled = true;

            try {
                // Get CSRF token
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                // Post comment to API
                const response = await fetch(`/following/api/activity-log/${updateId}/comment/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `content=${encodeURIComponent(comment)}`
                });

                const data = await response.json();
                
                if (data.success && data.comment) {
                    this.addComment(updateId, data.comment);
                    textarea.value = '';
                    
                    // Show success message
                    this.showNotification('Comment posted successfully', 'success');
                } else {
                    throw new Error(data.error || 'Failed to post comment');
                }
            } catch (error) {
                console.error('Error posting comment:', error);
                this.showNotification(error.message || 'Failed to post comment', 'error');
            } finally {
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }
        });
    }

    /**
     * Add comment to the list
     */
    addComment(updateId, commentData) {
        const commentsList = document.getElementById(`comments-list-${updateId}`);
        if (!commentsList) return;

        // Remove "no comments" message if present
        const noCommentsMsg = commentsList.querySelector('.text-center');
        if (noCommentsMsg) {
            noCommentsMsg.remove();
        }

        // Extract comment data
        const comment = typeof commentData === 'string' ? commentData : commentData.content || commentData;
        const commentId = commentData.id || Date.now();
        const username = commentData.username || commentData.user_display || 'You';
        const userInitial = username.charAt(0).toUpperCase();
        const timeAgo = commentData.time_ago || 'just now';

        const commentElement = document.createElement('div');
        commentElement.className = 'flex gap-3 p-3 bg-white rounded-lg border border-gray-100';
        commentElement.dataset.commentId = commentId;
        commentElement.innerHTML = `
            <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                ${userInitial}
            </div>
            <div class="flex-1">
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center gap-2">
                        <span class="font-medium text-gray-900">${username}</span>
                        <span class="text-xs text-gray-500">${timeAgo}</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <!-- Like/Dislike buttons -->
                        <button class="text-gray-400 hover:text-blue-600 transition-colors" 
                                data-action="like-comment" data-comment-id="${commentId}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"></path>
                            </svg>
                        </button>
                        <span class="text-xs text-gray-500" data-like-count="${commentId}">0</span>
                        
                        <button class="text-gray-400 hover:text-red-600 transition-colors ml-2" 
                                data-action="flag-comment" data-comment-id="${commentId}">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"></path>
                            </svg>
                        </button>
                    </div>
                </div>
                <p class="text-gray-700 text-sm">${this.escapeHtml(comment)}</p>
            </div>
        `;

        commentsList.appendChild(commentElement);
        
        // Bind actions for the new comment
        this.bindCommentActions(commentElement);
        
        // Update comment count
        const commentButton = document.querySelector(`[data-update-id="${updateId}"] [data-action="show-comments"] span`);
        if (commentButton) {
            const currentCount = parseInt(commentButton.textContent) || 0;
            commentButton.textContent = currentCount + 1;
        }
    }

    /**
     * Bind like button functionality for feed items
     */
    bindLikeButtons() {
        const likeButtons = document.querySelectorAll('[data-action="like-update"]');
        console.log(`FollowingPage: Found ${likeButtons.length} like buttons`);
        
        likeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Check authentication
                if (!this.isAuthenticated) {
                    this.showLoginPrompt('like updates');
                    return;
                }
                
                const updateId = button.dataset.updateId;
                this.handleUpdateLike(updateId, button);
            });
        });
    }

    /**
     * Handle feed item like
     */
    async handleUpdateLike(updateId, button) {
        try {
            // Toggle visual state immediately
            button.classList.toggle('text-blue-600');
            button.classList.toggle('text-gray-500');
            
            // Update count
            const countElement = button.querySelector(`[data-like-count="update-${updateId}"]`);
            if (countElement) {
                const currentCount = parseInt(countElement.textContent) || 0;
                countElement.textContent = button.classList.contains('text-blue-600') 
                    ? currentCount + 1 
                    : Math.max(0, currentCount - 1);
            }

            // TODO: Send to server API when endpoint is available
            console.log(`Liked activity update ${updateId}`);
        } catch (error) {
            console.error('Error liking update:', error);
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
        const councilLinkElement = updateCard.querySelector('a[href*="council_detail"]');
        
        if (!councilNameElement || !updateTextElement) return;
        
        const councilName = councilNameElement.textContent;
        const updateText = updateTextElement.textContent.trim();
        
        // Get the council detail page URL from the "View Council" link
        const shareUrl = councilLinkElement ? councilLinkElement.href : window.location.href;
        console.log(`FollowingPage: Share URL for council ${councilName}: ${shareUrl}`);
        
        // Use the full story text, not truncated
        const shareText = updateText;

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
                
                <!-- Preview what will be shared -->
                <div class="mb-4 p-3 bg-gray-50 rounded-lg">
                    <p class="text-sm text-gray-600 mb-1">You'll share:</p>
                    <p class="text-sm text-gray-900">"${shareText.length > 100 ? shareText.substring(0, 100) + '...' : shareText}"</p>
                    <p class="text-xs text-gray-500 mt-1">Link: ${councilName} details page</p>
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

    /**
     * Bind comment actions (like, flag)
     */
    bindCommentActions(commentElement) {
        // Like button
        const likeButton = commentElement.querySelector('[data-action="like-comment"]');
        if (likeButton) {
            likeButton.addEventListener('click', (e) => {
                e.preventDefault();
                const commentId = likeButton.dataset.commentId;
                this.handleCommentLike(commentId, likeButton);
            });
        }

        // Flag button
        const flagButton = commentElement.querySelector('[data-action="flag-comment"]');
        if (flagButton) {
            flagButton.addEventListener('click', (e) => {
                e.preventDefault();
                const commentId = flagButton.dataset.commentId;
                this.handleCommentFlag(commentId, commentElement);
            });
        }
    }

    /**
     * Handle comment like
     */
    async handleCommentLike(commentId, button) {
        try {
            // Toggle visual state immediately
            button.classList.toggle('text-blue-600');
            button.classList.toggle('text-gray-400');
            
            // Update count
            const countElement = button.parentElement.querySelector(`[data-like-count="${commentId}"]`);
            if (countElement) {
                const currentCount = parseInt(countElement.textContent) || 0;
                countElement.textContent = button.classList.contains('text-blue-600') 
                    ? currentCount + 1 
                    : Math.max(0, currentCount - 1);
            }

            // TODO: Send to server API when endpoint is available
            console.log(`Liked comment ${commentId}`);
        } catch (error) {
            console.error('Error liking comment:', error);
        }
    }

    /**
     * Handle comment flag
     */
    async handleCommentFlag(commentId, commentElement) {
        try {
            // Use existing flagging system
            if (window.flaggingSystem) {
                window.flaggingSystem.showFlagModal(
                    'ActivityLogComment',
                    commentId,
                    'Comment on activity update'
                );
            } else {
                console.error('Flagging system not available');
            }
        } catch (error) {
            console.error('Error flagging comment:', error);
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-600 text-white' :
            type === 'error' ? 'bg-red-600 text-white' :
            'bg-blue-600 text-white'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('opacity-0', 'transition-opacity', 'duration-300');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show login prompt for anonymous users
     */
    showLoginPrompt(action) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-xl max-w-md w-full mx-4 p-6">
                <div class="text-center">
                    <div class="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Sign in required</h3>
                    <p class="text-gray-600 mb-6">You need to be logged in to ${action}.</p>
                    
                    <div class="space-y-3">
                        <a href="/login/" class="block w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors">
                            Log In
                        </a>
                        <a href="/register/" class="block w-full border border-gray-300 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors">
                            Create Account
                        </a>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="block w-full text-gray-500 hover:text-gray-700 transition-colors">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    /**
     * Load existing comments for an activity
     */
    async loadComments(updateId) {
        try {
            const response = await fetch(`/following/api/activity-log/${updateId}/comments/`);
            const data = await response.json();
            
            if (data.success && data.comments) {
                const commentsList = document.getElementById(`comments-list-${updateId}`);
                if (!commentsList) return;
                
                // Clear existing content
                commentsList.innerHTML = '';
                
                if (data.comments.length > 0) {
                    data.comments.forEach(comment => {
                        // Check if comment is flagged and hidden
                        if (comment.flag_count >= 3) {
                            const hiddenComment = document.createElement('div');
                            hiddenComment.className = 'p-3 bg-gray-100 rounded-lg text-sm text-gray-500 italic';
                            hiddenComment.textContent = 'This comment has been hidden due to potential content violations';
                            commentsList.appendChild(hiddenComment);
                        } else {
                            this.addComment(updateId, comment);
                        }
                    });
                } else {
                    commentsList.innerHTML = `
                        <div class="text-sm text-gray-500 text-center py-4">
                            No comments yet. Be the first to comment!
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('Error loading comments:', error);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.followingPage = new FollowingPage();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FollowingPage;
}