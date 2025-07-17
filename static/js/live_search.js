// Enhanced Live Search with Modern UX
(function() {
    let searchInput;
    let searchResults;
    let searchTimeout;
    let currentFocus = -1;
    let isSearching = false;

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        searchInput = document.getElementById('live-search-input');
        searchResults = document.getElementById('live-search-results');
        
        if (!searchInput || !searchResults) return;

        setupSearch();
        setupKeyboardShortcuts();
        setupNotifications();
        setupGodModeDropdown();
    });

    function setupSearch() {
        let lastQuery = '';

        // Enhanced input handler with debouncing
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            // Reset focus when typing
            currentFocus = -1;
            
            if (query.length === 0) {
                hideResults();
                return;
            }

            if (query === lastQuery) return;
            lastQuery = query;

            // Clear previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }

            // Show loading state immediately for responsiveness
            if (query.length >= 2) {
                showLoadingState();
            }

            // Debounce search requests
            searchTimeout = setTimeout(() => {
                if (query.length >= 2) {
                    performSearch(query);
                } else {
                    hideResults();
                }
            }, 300);
        });

        // Enhanced keyboard navigation
        searchInput.addEventListener('keydown', function(e) {
            const items = searchResults.querySelectorAll('.search-result-item');
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    currentFocus = Math.min(currentFocus + 1, items.length - 1);
                    updateFocus(items);
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    currentFocus = Math.max(currentFocus - 1, -1);
                    updateFocus(items);
                    break;
                    
                case 'Enter':
                    e.preventDefault();
                    if (currentFocus >= 0 && items[currentFocus]) {
                        const link = items[currentFocus].querySelector('a');
                        if (link) {
                            window.location.href = link.href;
                        }
                    }
                    break;
                    
                case 'Escape':
                    hideResults();
                    searchInput.blur();
                    break;
            }
        });

        // Hide results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                hideResults();
            }
        });

        // Show results when focusing back on input (if has content)
        searchInput.addEventListener('focus', function() {
            if (this.value.trim().length >= 2) {
                const existingResults = searchResults.querySelector('.search-content');
                if (existingResults && existingResults.children.length > 0) {
                    showResults();
                }
            }
        });
    }

    function setupKeyboardShortcuts() {
        // Cmd/Ctrl + K to focus search
        document.addEventListener('keydown', function(e) {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });
    }

    function setupNotifications() {
        const notifToggle = document.getElementById('notif-toggle');
        const notifMenu = document.getElementById('notif-menu');
        const markAllReadBtn = document.getElementById('mark-all-read');

        if (notifToggle && notifMenu) {
            // Toggle notification menu
            notifToggle.addEventListener('click', function(e) {
                e.stopPropagation();
                notifMenu.classList.toggle('hidden');
                
                // Close search results when opening notifications
                if (!notifMenu.classList.contains('hidden')) {
                    hideResults();
                }
            });

            // Close notifications when clicking outside
            document.addEventListener('click', function(e) {
                if (!notifToggle.contains(e.target) && !notifMenu.contains(e.target)) {
                    notifMenu.classList.add('hidden');
                }
            });

            // Mark all notifications as read
            if (markAllReadBtn) {
                markAllReadBtn.addEventListener('click', function() {
                    fetch('/notifications/mark-all-read/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrfToken(),
                            'Content-Type': 'application/json',
                        },
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Update UI to show all notifications as read
                            const notificationItems = document.querySelectorAll('.notification-item');
                            notificationItems.forEach(item => {
                                item.classList.remove('bg-blue-50', 'border-l-4', 'border-l-blue-500');
                                const unreadDot = item.querySelector('.w-2.h-2.bg-blue-500');
                                if (unreadDot) {
                                    unreadDot.remove();
                                }
                            });
                            
                            // Hide the badge
                            const badge = notifToggle.querySelector('.animate-pulse');
                            if (badge) {
                                badge.remove();
                            }
                            
                            // Hide the mark all read button
                            markAllReadBtn.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('Error marking notifications as read:', error);
                    });
                });
            }

            // Hover to mark individual notifications as read
            const notificationItems = document.querySelectorAll('.notification-item[data-read="false"]');
            notificationItems.forEach(item => {
                let hoverTimeout;
                
                item.addEventListener('mouseenter', function() {
                    const notificationId = this.dataset.notificationId;
                    
                    // Mark as read after hovering for 1 second
                    hoverTimeout = setTimeout(() => {
                        markNotificationAsRead(notificationId, this);
                    }, 1000);
                });
                
                item.addEventListener('mouseleave', function() {
                    if (hoverTimeout) {
                        clearTimeout(hoverTimeout);
                    }
                });
            });
        }
    }

    function markNotificationAsRead(notificationId, element) {
        fetch(`/notifications/${notificationId}/mark-read/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the element to show as read
                element.classList.remove('bg-blue-50', 'border-l-4', 'border-l-blue-500');
                element.dataset.read = 'true';
                
                // Remove the unread dot
                const unreadDot = element.querySelector('.w-2.h-2.bg-blue-500');
                if (unreadDot) {
                    unreadDot.remove();
                }
                
                // Update the notification count
                updateNotificationCount();
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }

    function updateNotificationCount() {
        const unreadItems = document.querySelectorAll('.notification-item[data-read="false"]');
        const badge = document.querySelector('#notif-toggle .animate-pulse');
        const markAllBtn = document.getElementById('mark-all-read');
        
        if (unreadItems.length === 0) {
            if (badge) {
                badge.remove();
            }
            if (markAllBtn) {
                markAllBtn.style.display = 'none';
            }
        } else if (badge) {
            badge.textContent = unreadItems.length;
        }
    }

    function showLoadingState() {
        searchResults.innerHTML = `
            <div class="search-content">
                <div class="p-6 text-center">
                    <div class="inline-flex items-center space-x-2">
                        <div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
                        <span class="text-gray-600">Searching councils...</span>
                    </div>
                </div>
            </div>
        `;
        showResults();
    }

    function performSearch(query) {
        if (isSearching) return;
        
        isSearching = true;
        
        fetch(`/api/councils/search/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                displayResults(data || [], query);
            })
            .catch(error => {
                console.error('Search error:', error);
                displayError();
            })
            .finally(() => {
                isSearching = false;
            });
    }

    function displayResults(councils, query) {
        if (councils.length === 0) {
            displayNoResults(query);
            return;
        }

        const resultsHtml = councils.map((council, index) => {
            const highlightedName = highlightQuery(council.name, query);
            const typeIcon = getCouncilTypeIcon(council.type || 'District');
            const region = council.region || 'Unknown region';
            const type = council.type || 'Council';
            
            return `
                <div class="search-result-item group cursor-pointer border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors" data-index="${index}">
                    <a href="/councils/${council.slug}/" class="block p-4">
                        <div class="flex items-center space-x-3">
                            <div class="flex-shrink-0">
                                <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-lg">
                                    ${typeIcon}
                                </div>
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between">
                                    <h3 class="text-sm font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                                        ${highlightedName}
                                    </h3>
                                    <span class="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                                        ${type}
                                    </span>
                                </div>
                                <p class="text-sm text-gray-600 mt-1">
                                    <span class="inline-flex items-center">
                                        <svg class="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                                        </svg>
                                        ${region}
                                    </span>
                                </p>
                            </div>
                            <div class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                <svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                </svg>
                            </div>
                        </div>
                    </a>
                </div>
            `;
        }).join('');

        searchResults.innerHTML = `
            <div class="search-content">
                <div class="p-3 bg-gray-50 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <p class="text-sm text-gray-600">
                            <span class="font-medium">${councils.length}</span> 
                            ${councils.length === 1 ? 'council' : 'councils'} found
                        </p>
                        <div class="text-xs text-gray-500">
                            Use ↑↓ to navigate, Enter to select
                        </div>
                    </div>
                </div>
                ${resultsHtml}
                <div class="p-3 bg-gray-50 border-t border-gray-200">
                    <a href="/search/?q=${encodeURIComponent(query)}" class="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center justify-center">
                        View all results for "${query}"
                        <svg class="ml-1 w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                        </svg>
                    </a>
                </div>
            </div>
        `;

        showResults();
    }

    function displayNoResults(query) {
        searchResults.innerHTML = `
            <div class="search-content">
                <div class="p-8 text-center">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No councils found</h3>
                    <p class="mt-1 text-sm text-gray-500">
                        We couldn't find any councils matching "<strong>${escapeHtml(query)}</strong>"
                    </p>
                    <div class="mt-4">
                        <a href="/councils/" class="text-sm text-blue-600 hover:text-blue-800 font-medium">
                            Browse all councils →
                        </a>
                    </div>
                </div>
            </div>
        `;
        showResults();
    }

    function displayError() {
        searchResults.innerHTML = `
            <div class="search-content">
                <div class="p-6 text-center">
                    <svg class="mx-auto h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p class="mt-2 text-sm text-gray-600">
                        Search temporarily unavailable. Please try again.
                    </p>
                </div>
            </div>
        `;
        showResults();
    }

    function showResults() {
        searchResults.classList.remove('hidden');
    }

    function hideResults() {
        searchResults.classList.add('hidden');
        currentFocus = -1;
    }

    function updateFocus(items) {
        // Remove focus from all items
        items.forEach((item, index) => {
            if (index === currentFocus) {
                item.classList.add('bg-blue-50');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('bg-blue-50');
            }
        });
    }

    function highlightQuery(text, query) {
        if (!query) return escapeHtml(text);
        
        const escapedText = escapeHtml(text);
        const escapedQuery = escapeHtml(query);
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        
        return escapedText.replace(regex, '<mark class="bg-yellow-200 text-yellow-800 font-medium rounded px-1">$1</mark>');
    }

    function getCouncilTypeIcon(type) {
        const icons = {
            'District': '🏛️',
            'Borough': '🏢',
            'City': '🌆',
            'County': '🗺️',
            'Metropolitan': '🏙️',
            'Unitary': '⭐',
            'Parish': '⛪',
            'Town': '🏘️'
        };
        
        return icons[type] || '🏛️';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function setupGodModeDropdown() {
        const godModeToggle = document.getElementById('god-mode-toggle');
        const godModeMenu = document.getElementById('god-mode-menu');
        const godModeDropdown = document.getElementById('god-mode-dropdown');

        if (godModeToggle && godModeMenu && godModeDropdown) {
            let hoverTimeout;

            function showDropdown() {
                clearTimeout(hoverTimeout);
                godModeMenu.classList.remove('hidden');
                // Force a reflow then add the visible styles
                setTimeout(() => {
                    godModeMenu.style.opacity = '1';
                    godModeMenu.style.transform = 'scale(1)';
                }, 10);
                godModeToggle.setAttribute('aria-expanded', 'true');
                
                // Close other dropdowns
                const notifMenu = document.getElementById('notif-menu');
                if (notifMenu) {
                    notifMenu.classList.add('hidden');
                }
                hideResults();
            }

            function hideDropdown() {
                godModeMenu.style.opacity = '0';
                godModeMenu.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    godModeMenu.classList.add('hidden');
                }, 200);
                godModeToggle.setAttribute('aria-expanded', 'false');
            }

            // Show dropdown on hover
            godModeDropdown.addEventListener('mouseenter', function() {
                showDropdown();
            });

            // Hide dropdown when leaving the entire dropdown area
            godModeDropdown.addEventListener('mouseleave', function() {
                hoverTimeout = setTimeout(() => {
                    hideDropdown();
                }, 150); // Small delay to prevent flickering
            });

            // Toggle dropdown on click (for accessibility)
            godModeToggle.addEventListener('click', function(e) {
                e.stopPropagation();
                clearTimeout(hoverTimeout);
                
                const isHidden = godModeMenu.classList.contains('hidden');
                if (isHidden) {
                    showDropdown();
                } else {
                    hideDropdown();
                }
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!godModeDropdown.contains(e.target)) {
                    clearTimeout(hoverTimeout);
                    hideDropdown();
                }
            });

            // Close dropdown when pressing Escape
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && !godModeMenu.classList.contains('hidden')) {
                    clearTimeout(hoverTimeout);
                    hideDropdown();
                    godModeToggle.focus();
                }
            });
        }
    }

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
    }

    // Maintain backward compatibility with old API
    function attachLiveSearch(input, resultsContainer) {
        // Legacy function for compatibility
        console.warn('attachLiveSearch is deprecated. New search functionality is automatically initialized.');
    }

    // Export for global access if needed
    window.attachLiveSearch = attachLiveSearch;
    window.LiveSearch = {
        hideResults: hideResults,
        showResults: showResults
    };
})();
