/**
 * Leaderboards JavaScript functionality
 * Handles per capita toggle, year selector, sort order toggle with dynamic titles
 */

// Store original category data for dynamic title switching
const LeaderboardCategories = {
    'total-debt': {
        name: 'Total Debt',
        description: 'Councils with the highest total debt levels'
    },
    'interest-payments': {
        name: 'Interest Payments', 
        description: 'Councils paying the most in interest'
    },
    'current-liabilities': {
        name: 'Current Liabilities',
        description: 'Councils with highest short-term liabilities'
    },
    'long-term-liabilities': {
        name: 'Long-term Liabilities',
        description: 'Councils with highest long-term debt obligations'
    },
    'reserves-balances': {
        name: 'Reserves & Balances',
        description: 'Councils with the highest usable reserves'
    },
    'council-tax-income': {
        name: 'Council Tax Income',
        description: 'Councils generating the most council tax revenue'
    }
};

/**
 * Update category titles based on sort direction
 * @param {boolean} isReversed - Whether sorting is reversed
 * @param {string} currentCategory - Current category slug
 */
function updateCategoryTitles(isReversed, currentCategory) {
    const titleElement = document.getElementById('category-title');
    const descElement = document.getElementById('category-description');
    
    if (currentCategory === 'contributors' || !LeaderboardCategories[currentCategory]) {
        return; // Don't change contributors or unknown categories
    }
    
    const data = LeaderboardCategories[currentCategory];
    if (isReversed) {
        // Replace words for reversed sorting
        const reversedName = data.name
            .replace('Highest', 'Lowest')
            .replace('highest', 'lowest')
            .replace('most', 'least');
        const reversedDesc = data.description
            .replace('highest', 'lowest')
            .replace('most', 'least');
        
        if (titleElement) titleElement.textContent = reversedName;
        if (descElement) descElement.textContent = reversedDesc;
    } else {
        if (titleElement) titleElement.textContent = data.name;
        if (descElement) descElement.textContent = data.description;
    }
}

/**
 * Generic per capita toggle functionality 
 * Can be reused across different pages
 */
function initPerCapitaToggle() {
    const perCapitaToggle = document.getElementById('per-capita-toggle');
    if (perCapitaToggle) {
        console.log('Per capita toggle found');
        perCapitaToggle.addEventListener('change', function(e) {
            console.log('Per capita changed to:', e.target.checked);
            const url = new URL(window.location);
            if (e.target.checked) {
                url.searchParams.set('per_capita', 'true');
            } else {
                url.searchParams.delete('per_capita');
            }
            window.location.href = url.toString();
        });
    }
}

/**
 * Year selector functionality
 */
function initYearSelector() {
    const yearSelect = document.getElementById('year-select');
    if (yearSelect) {
        console.log('Year selector found');
        yearSelect.addEventListener('change', function(e) {
            console.log('Year changed to:', e.target.value);
            const url = new URL(window.location);
            url.searchParams.set('year', e.target.value);
            window.location.href = url.toString();
        });
    }
}

/**
 * Sort order toggle functionality
 */
function initSortOrderToggle(currentCategory) {
    const sortToggle = document.getElementById('sort-order-toggle');
    if (sortToggle) {
        console.log('Sort toggle found');
        sortToggle.addEventListener('change', function(e) {
            console.log('Sort order changed to:', e.target.checked);
            const url = new URL(window.location);
            if (e.target.checked) {
                url.searchParams.set('reverse', 'true');
            } else {
                url.searchParams.delete('reverse');
            }
            window.location.href = url.toString();
        });
    }
}

/**
 * Initialize all leaderboard controls
 * @param {string} currentCategory - Current category slug
 * @param {boolean} reversSort - Current reverse sort state  
 */
function initLeaderboards(currentCategory, reverseSort) {
    console.log('Initializing leaderboard controls for category:', currentCategory);
    
    // Initialize all toggles and selectors
    initPerCapitaToggle();
    initYearSelector();
    initSortOrderToggle(currentCategory);
    
    // Set initial title state
    updateCategoryTitles(reverseSort, currentCategory);
    
    console.log('Leaderboard controls initialized');
}

// Export functions for use in other modules
window.LeaderboardUtils = {
    initPerCapitaToggle,
    initYearSelector,
    initSortOrderToggle,
    updateCategoryTitles,
    initLeaderboards
};