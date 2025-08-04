/**
 * About Page GitHub Integration
 * Fetches live GitHub statistics and contributors via AJAX
 */

class AboutGitHubLoader {
    constructor() {
        this.baseUrl = '/api/github';
        this.init();
    }

    init() {
        console.log('🔄 About GitHub Loader initialized');
        this.loadGitHubStats();
        this.loadContributors();
    }

    showSpinner(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="flex items-center justify-center py-4">
                    <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    <span class="ml-2 text-sm text-slate-600">Loading...</span>
                </div>
            `;
        }
    }

    showError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <div class="text-red-600 text-sm">${message}</div>
                </div>
            `;
        }
    }

    async loadGitHubStats() {
        console.log('📊 Loading GitHub repository statistics...');
        
        // Show loading spinners
        this.showSpinner('github-stars');
        this.showSpinner('github-forks');
        this.showSpinner('github-contributors-count');
        this.showSpinner('github-issues');
        this.showSpinner('github-commits');
        this.showSpinner('github-pull-requests');
        this.showSpinner('github-closed-issues');

        try {
            const response = await fetch(`${this.baseUrl}/stats/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                }
            });

            console.log('📊 GitHub stats response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('📊 GitHub stats data received:', data);

            // Update stats in the UI
            this.updateStat('github-stars', data.stars || 0);
            this.updateStat('github-forks', data.forks || 0);
            this.updateStat('github-contributors-count', data.contributors_count || 0);
            this.updateStat('github-issues', data.open_issues || 0);
            this.updateStat('github-commits', data.commits || 0);
            this.updateStat('github-pull-requests', data.pull_requests || 0);
            this.updateStat('github-closed-issues', data.closed_issues || 0);

        } catch (error) {
            console.error('❌ Error loading GitHub stats:', error);
            this.showError('github-stars', 'Error loading');
            this.showError('github-forks', 'Error loading');
            this.showError('github-contributors-count', 'Error loading');
            this.showError('github-issues', 'Error loading');
        }
    }

    async loadContributors() {
        console.log('👥 Loading GitHub contributors...');
        
        const contributorsContainer = document.getElementById('github-contributors');
        if (!contributorsContainer) {
            console.warn('👥 Contributors container not found');
            return;
        }

        // Show loading spinner
        contributorsContainer.innerHTML = `
            <div class="flex items-center justify-center py-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span class="ml-3 text-slate-600">Loading contributors...</span>
            </div>
        `;

        try {
            const response = await fetch(`${this.baseUrl}/contributors/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                }
            });

            console.log('👥 Contributors response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('👥 Contributors data received:', data);

            if (data.contributors && data.contributors.length > 0) {
                this.renderContributors(data.contributors);
            } else {
                contributorsContainer.innerHTML = `
                    <div class="text-center py-8 text-slate-600">
                        No contributors data available
                    </div>
                `;
            }

        } catch (error) {
            console.error('❌ Error loading contributors:', error);
            contributorsContainer.innerHTML = `
                <div class="text-center py-8">
                    <div class="text-red-600">Error loading contributors: ${error.message}</div>
                    <button onclick="aboutGitHub.loadContributors()" class="mt-2 text-blue-600 hover:text-blue-800 text-sm">
                        Try again
                    </button>
                </div>
            `;
        }
    }

    updateStat(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            console.log(`📊 Updated ${elementId} to:`, value);
        } else {
            console.warn(`📊 Element ${elementId} not found`);
        }
    }

    renderContributors(contributors) {
        const contributorsContainer = document.getElementById('github-contributors');
        if (!contributorsContainer) return;

        const contributorElements = contributors.map(contributor => `
            <a href="${contributor.html_url}" 
               target="_blank" 
               rel="noopener" 
               class="contributor-card group relative bg-white rounded-lg p-4 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border border-slate-100"
               title="${contributor.login} - ${contributor.contributions} contribution${contributor.contributions !== 1 ? 's' : ''}">
                <div class="relative">
                    ${contributor.avatar_url 
                        ? `<img src="${contributor.avatar_url}" 
                               alt="${contributor.login}" 
                               class="w-16 h-16 rounded-full mx-auto mb-2 ring-2 ring-white group-hover:ring-blue-100 transition-all">` 
                        : `<div class="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center mx-auto mb-2 text-xl font-bold ring-2 ring-white group-hover:ring-blue-100 transition-all">
                               ${contributor.login.charAt(0).toUpperCase()}
                           </div>`
                    }
                    
                    <!-- Contribution badge -->
                    <div class="absolute -bottom-1 left-1/2 transform -translate-x-1/2 bg-white rounded-full px-2 py-0.5 text-xs font-medium text-slate-700 shadow-sm border border-slate-200">
                        ${contributor.contributions}
                    </div>
                </div>
                
                <div class="text-center mt-3">
                    <div class="text-sm font-medium text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                        ${contributor.login}
                    </div>
                    <div class="text-xs text-slate-500">
                        ${contributor.contributions === 1 ? '1 contribution' : `${contributor.contributions} contributions`}
                    </div>
                </div>
            </a>
        `).join('');

        contributorsContainer.innerHTML = `
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                ${contributorElements}
            </div>
        `;

        console.log(`👥 Rendered ${contributors.length} contributors`);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM loaded, initializing About GitHub loader...');
    window.aboutGitHub = new AboutGitHubLoader();
});