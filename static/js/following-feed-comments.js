/**
 * Following Feed Activity Log Comments
 * 
 * Handles commenting functionality for ActivityLog entries in the Following feed.
 * Provides real-time commenting, loading, and interaction features.
 */

class FollowingFeedComments {
    constructor() {
        this.init();
    }
    
    init() {
        // Bind event listeners
        this.bindToggleComments();
        this.bindCommentForms();
        this.bindCommentActions();
    }
    
    /**
     * Toggle comments visibility and load comments when needed
     */
    bindToggleComments() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('toggle-comments')) {
                e.preventDefault();
                const activityLogId = e.target.dataset.activityLogId;
                const container = document.querySelector(`[data-activity-log-id="${activityLogId}"] .comments-container`);
                
                if (container.classList.contains('hidden')) {
                    this.loadComments(activityLogId);
                    container.classList.remove('hidden');
                    e.target.textContent = 'Hide Comments';
                } else {
                    container.classList.add('hidden');
                    e.target.textContent = 'Show Comments';
                }
            }
        });
    }
    
    /**
     * Bind comment form submissions
     */
    bindCommentForms() {
        document.addEventListener('submit', (e) => {
            if (e.target.classList.contains('comment-form')) {
                e.preventDefault();
                this.submitComment(e.target);
            }
        });
    }
    
    /**
     * Bind comment actions (like, reply, etc.)
     */
    bindCommentActions() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('like-comment')) {
                e.preventDefault();
                this.likeComment(e.target);
            } else if (e.target.classList.contains('reply-comment')) {
                e.preventDefault();
                this.showReplyForm(e.target);
            }
        });
    }
    
    /**
     * Load comments for an ActivityLog entry
     */
    async loadComments(activityLogId) {
        try {
            const container = document.querySelector(`[data-activity-log-id="${activityLogId}"] .comments-list`);
            container.innerHTML = '<div class="flex justify-center py-4"><div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div></div>';
            
            const response = await fetch(`/following/api/activity-log/${activityLogId}/comments/`);
            const data = await response.json();
            
            if (data.success) {
                this.renderComments(container, data.comments);
            } else {
                container.innerHTML = `<div class="text-red-600 text-sm py-4">Error loading comments: ${data.error}</div>`;
            }
        } catch (error) {
            console.error('Error loading comments:', error);
            const container = document.querySelector(`[data-activity-log-id="${activityLogId}"] .comments-list`);
            container.innerHTML = '<div class="text-red-600 text-sm py-4">Failed to load comments. Please try again.</div>';
        }
    }
    
    /**
     * Render comments in the container
     */
    renderComments(container, comments) {
        if (comments.length === 0) {
            container.innerHTML = '<div class="text-gray-500 text-sm py-4">No comments yet. Be the first to comment!</div>';
            return;
        }
        
        const commentsHtml = comments.map(comment => this.renderComment(comment)).join('');
        container.innerHTML = commentsHtml;
    }
    
    /**
     * Render a single comment with replies
     */
    renderComment(comment) {
        const repliesHtml = comment.replies.map(reply => this.renderReply(reply)).join('');
        
        return `
            <div class="comment mb-4" data-comment-id="${comment.id}">
                <div class="flex space-x-3">
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <span class="text-blue-600 text-sm font-medium">${comment.user.username.charAt(0).toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="flex-1">
                        <div class="bg-gray-50 rounded-lg px-3 py-2">
                            <div class="flex items-center space-x-2 mb-1">
                                <span class="font-medium text-sm text-gray-900">${comment.user.display_name}</span>
                                <span class="text-xs text-gray-500">${this.formatDate(comment.created_at)}</span>
                            </div>
                            <p class="text-sm text-gray-700">${this.escapeHtml(comment.content)}</p>
                        </div>
                        <div class="flex items-center space-x-4 mt-2">
                            <button class="like-comment text-xs text-gray-500 hover:text-blue-600 flex items-center" data-comment-id="${comment.id}">
                                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
                                </svg>
                                <span class="like-count">${comment.like_count}</span>
                            </button>
                            <button class="reply-comment text-xs text-gray-500 hover:text-blue-600" data-comment-id="${comment.id}">
                                Reply
                            </button>
                        </div>
                        
                        <!-- Replies -->
                        ${repliesHtml ? `<div class="replies mt-3 ml-4 border-l-2 border-gray-200 pl-4">${repliesHtml}</div>` : ''}
                        
                        <!-- Reply Form (initially hidden) -->
                        <div class="reply-form-container mt-3 hidden" data-parent-id="${comment.id}">
                            <form class="reply-form">
                                <div class="flex space-x-3">
                                    <div class="flex-shrink-0">
                                        <div class="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                                            <span class="text-blue-600 text-xs font-medium">${this.getCurrentUserInitial()}</span>
                                        </div>
                                    </div>
                                    <div class="flex-1">
                                        <textarea name="content" placeholder="Write a reply..." class="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 resize-none" rows="2"></textarea>
                                        <div class="mt-2 flex justify-end space-x-2">
                                            <button type="button" class="cancel-reply px-2 py-1 text-xs text-gray-600 hover:text-gray-800">Cancel</button>
                                            <button type="submit" class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Reply</button>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Render a reply to a comment
     */
    renderReply(reply) {
        return `
            <div class="reply mb-3" data-comment-id="${reply.id}">
                <div class="flex space-x-2">
                    <div class="flex-shrink-0">
                        <div class="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                            <span class="text-blue-600 text-xs font-medium">${reply.user.username.charAt(0).toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="flex-1">
                        <div class="bg-gray-50 rounded-lg px-2 py-1">
                            <div class="flex items-center space-x-2 mb-1">
                                <span class="font-medium text-xs text-gray-900">${reply.user.display_name}</span>
                                <span class="text-xs text-gray-500">${this.formatDate(reply.created_at)}</span>
                            </div>
                            <p class="text-xs text-gray-700">${this.escapeHtml(reply.content)}</p>
                        </div>
                        <div class="flex items-center space-x-3 mt-1">
                            <button class="like-comment text-xs text-gray-500 hover:text-blue-600 flex items-center" data-comment-id="${reply.id}">
                                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
                                </svg>
                                <span class="like-count">${reply.like_count}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Submit a comment
     */
    async submitComment(form) {
        try {
            const activityLogId = form.dataset.activityLogId;
            const content = form.querySelector('textarea[name="content"]').value.trim();
            const parentId = form.querySelector('input[name="parent_id"]')?.value;
            
            if (!content) {
                this.showError(form, 'Please enter a comment');
                return;
            }
            
            // Show loading state
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Posting...';
            submitBtn.disabled = true;
            
            const formData = new FormData();
            formData.append('content', content);
            if (parentId) formData.append('parent_id', parentId);
            formData.append('csrfmiddlewaretoken', this.getCSRFToken());
            
            const response = await fetch(`/following/api/activity-log/${activityLogId}/comment/`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Clear form
                form.reset();
                
                // Reload comments
                await this.loadComments(activityLogId);
                
                // Update comment count
                this.updateCommentCount(activityLogId, 1);
                
                // Hide reply form if it was a reply
                if (parentId) {
                    const replyContainer = form.closest('.reply-form-container');
                    replyContainer.classList.add('hidden');
                }
                
                this.showSuccess(form, 'Comment posted successfully!');
            } else {
                this.showError(form, data.error || 'Failed to post comment');
            }
            
            // Restore button
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
            
        } catch (error) {
            console.error('Error submitting comment:', error);
            this.showError(form, 'Failed to post comment. Please try again.');
            
            // Restore button
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }
    
    /**
     * Like a comment
     */
    async likeComment(button) {
        try {
            const commentId = button.dataset.commentId;
            const likeCountSpan = button.querySelector('.like-count');
            const currentCount = parseInt(likeCountSpan.textContent);
            
            const formData = new FormData();
            formData.append('action', 'like');
            formData.append('csrfmiddlewaretoken', this.getCSRFToken());
            
            const response = await fetch(`/following/api/comment/${commentId}/like/`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                likeCountSpan.textContent = data.like_count;
                if (data.liked) {
                    button.classList.add('text-red-500');
                } else {
                    button.classList.remove('text-red-500');
                }
            }
        } catch (error) {
            console.error('Error liking comment:', error);
        }
    }
    
    /**
     * Show reply form
     */
    showReplyForm(button) {
        const commentId = button.dataset.commentId;
        const replyContainer = document.querySelector(`[data-parent-id="${commentId}"]`);
        
        if (replyContainer) {
            replyContainer.classList.toggle('hidden');
            
            // Focus textarea if showing
            if (!replyContainer.classList.contains('hidden')) {
                const textarea = replyContainer.querySelector('textarea');
                textarea.focus();
                
                // Add cancel functionality
                const cancelBtn = replyContainer.querySelector('.cancel-reply');
                cancelBtn.onclick = () => {
                    replyContainer.classList.add('hidden');
                    replyContainer.querySelector('textarea').value = '';
                };
                
                // Handle reply form submission
                const replyForm = replyContainer.querySelector('.reply-form');
                replyForm.onsubmit = (e) => {
                    e.preventDefault();
                    
                    // Create a temporary form element with the required data
                    const tempForm = document.createElement('form');
                    tempForm.className = 'comment-form';
                    tempForm.dataset.activityLogId = button.closest('[data-activity-log-id]').dataset.activityLogId;
                    
                    const contentInput = document.createElement('textarea');
                    contentInput.name = 'content';
                    contentInput.value = replyForm.querySelector('textarea').value;
                    tempForm.appendChild(contentInput);
                    
                    const parentInput = document.createElement('input');
                    parentInput.type = 'hidden';
                    parentInput.name = 'parent_id';
                    parentInput.value = commentId;
                    tempForm.appendChild(parentInput);
                    
                    this.submitComment(tempForm);
                };
            }
        }
    }
    
    /**
     * Update comment count display
     */
    updateCommentCount(activityLogId, delta) {
        const countElement = document.querySelector(`[data-activity-log-id="${activityLogId}"] .comment-count`);
        if (countElement) {
            const currentCount = parseInt(countElement.textContent);
            const newCount = currentCount + delta;
            countElement.textContent = newCount;
            
            // Update pluralization
            const commentText = countElement.nextSibling;
            if (commentText && commentText.nodeType === Node.TEXT_NODE) {
                commentText.textContent = newCount === 1 ? ' comment' : ' comments';
            }
        }
    }
    
    /**
     * Utility functions
     */
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    getCurrentUserInitial() {
        // Try to get from a data attribute or default to 'U'
        return document.body.dataset.userInitial || 'U';
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        
        return date.toLocaleDateString();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showSuccess(form, message) {
        this.showMessage(form, message, 'success');
    }
    
    showError(form, message) {
        this.showMessage(form, message, 'error');
    }
    
    showMessage(form, message, type) {
        // Remove existing messages
        const existingMessage = form.querySelector('.form-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.className = `form-message text-sm mt-2 ${type === 'success' ? 'text-green-600' : 'text-red-600'}`;
        messageDiv.textContent = message;
        
        // Insert after form
        form.appendChild(messageDiv);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new FollowingFeedComments();
});