import React, { useState, useEffect, useCallback } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { TouchBackend } from 'react-dnd-touch-backend';
import { isMobile } from 'react-device-detect';
import SimpleComparison from './comparison/SimpleComparison';
import LoadingSpinner from './LoadingSpinner';
import ErrorBoundary from './ErrorBoundary';

/**
 * Main React application for the GOV.UK-inspired Council Comparison Basket
 * Features:
 * - Up to 6 councils comparison
 * - Drag-and-drop reordering of councils and characteristics
 * - Cross-year comparison
 * - Save as list functionality
 * - CSV/JSON export
 * - Responsive mobile-first design
 */
const ComparisonBasketApp = ({ initialData = {}, onComparisonToggle }) => {
	// State management
	const [councils, setCouncils] = useState(initialData.councils || []);
	const [selectedFields, setSelectedFields] = useState(initialData.selectedFields || []);
	const [selectedYears, setSelectedYears] = useState(initialData.selectedYears || []);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);
	const [notification, setNotification] = useState(null);
	const [showComparison, setShowComparison] = useState(false);

	// Configuration
	const [config] = useState({
		maxCouncils: 6,
		apiUrls: {
			addToBasket: (slug) => `/compare/add/${slug}/`,
			removeFromBasket: (slug) => `/compare/remove/${slug}/`,
			clearBasket: '/compare/clear/',
			getBasketData: '/api/comparison/basket/',
			getFieldData: '/api/comparison/fields/',
			getYearData: '/api/comparison/years/',
			saveAsList: '/lists/create/',
			exportData: '/api/comparison/export/',
		},
		csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
					getCsrfTokenFromCookie(),
		availableFields: initialData.availableFields || [],
		availableYears: initialData.availableYears || [],
	});

	/**
	 * Get CSRF token from cookie as fallback
	 */
	function getCsrfTokenFromCookie() {
		const name = 'csrftoken';
		const cookies = document.cookie.split(';');
		for (let cookie of cookies) {
			const [cookieName, value] = cookie.trim().split('=');
			if (cookieName === name) {
				return decodeURIComponent(value);
			}
		}
		return '';
	}

	/**
	 * Show notification message to user
	 */
	const showNotification = useCallback((message, type = 'success', duration = 4000) => {
		setNotification({ message, type });
		setTimeout(() => setNotification(null), duration);
	}, []);

	/**
	 * Generic API call handler with error handling
	 */
	const apiCall = useCallback(async (url, options = {}) => {
		try {
			setError(null);
			const response = await fetch(url, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded',
					'X-CSRFToken': config.csrfToken,
					...options.headers,
				},
				...options,
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			return await response.json();
		} catch (err) {
			console.error('API call failed:', err);
			setError(err.message);
			showNotification(`Error: ${err.message}`, 'error');
			throw err;
		}
	}, [config.csrfToken, showNotification]);

	/**
	 * Add council to comparison basket
	 */
	const addCouncilToBasket = useCallback(async (councilSlug) => {
		if (councils.length >= config.maxCouncils) {
			showNotification(`Maximum ${config.maxCouncils} councils allowed in basket`, 'warning');
			return;
		}

		try {
			setLoading(true);
			const data = await apiCall(config.apiUrls.addToBasket(councilSlug), {
				method: 'POST',
			});

			if (data.success) {
				setCouncils(prev => {
					// Don't add if already exists
					const exists = prev.some(council => council.slug === councilSlug);
					if (!exists && data.council) {
						return [...prev, data.council];
					}
					return prev;
				});
				showNotification(`${data.council?.name} added to comparison basket`, 'success');
			}
		} catch (err) {
			// Error already handled in apiCall
		} finally {
			setLoading(false);
		}
	}, [councils.length, config.maxCouncils, config.apiUrls.addToBasket, apiCall, showNotification]);

	/**
	 * Remove council from comparison basket
	 */
	const removeCouncilFromBasket = useCallback(async (councilSlug) => {
		try {
			setLoading(true);
			const data = await apiCall(config.apiUrls.removeFromBasket(councilSlug), {
				method: 'POST',
			});

			if (data.success) {
				setCouncils(prev => prev.filter(council => council.slug !== councilSlug));
				showNotification(`Council removed from basket`, 'success');
			}
		} catch (err) {
			// Error already handled in apiCall
		} finally {
			setLoading(false);
		}
	}, [config.apiUrls.removeFromBasket, apiCall, showNotification]);

	/**
	 * Clear entire comparison basket
	 */
	const clearBasket = useCallback(async () => {
		if (!window.confirm('Are you sure you want to clear your entire comparison basket?')) {
			return;
		}

		try {
			setLoading(true);
			const data = await apiCall(config.apiUrls.clearBasket, {
				method: 'POST',
			});

			if (data.success) {
				setCouncils([]);
				setSelectedFields([]);
				setShowComparison(false);
				showNotification('Comparison basket cleared', 'success');
			}
		} catch (err) {
			// Error already handled in apiCall
		} finally {
			setLoading(false);
		}
	}, [config.apiUrls.clearBasket, apiCall, showNotification]);

	/**
	 * Reorder councils in basket (drag & drop)
	 */
	const reorderCouncils = useCallback((fromIndex, toIndex) => {
		setCouncils(prevCouncils => {
			const newCouncils = [...prevCouncils];
			const [movedCouncil] = newCouncils.splice(fromIndex, 1);
			newCouncils.splice(toIndex, 0, movedCouncil);
			return newCouncils;
		});
		showNotification('Council order updated', 'success', 2000);
	}, [showNotification]);

	/**
	 * Reorder comparison fields (drag & drop)
	 */
	const reorderFields = useCallback((fromIndex, toIndex) => {
		setSelectedFields(prevFields => {
			const newFields = [...prevFields];
			const [movedField] = newFields.splice(fromIndex, 1);
			newFields.splice(toIndex, 0, movedField);
			return newFields;
		});
		showNotification('Field order updated', 'success', 2000);
	}, [showNotification]);

	/**
	 * Save current basket as a custom list
	 */
	const saveAsListApi = useCallback(async (listName, description = '') => {
		try {
			setLoading(true);
			const data = await apiCall(config.apiUrls.saveAsList, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					name: listName,
					description: description,
					councils: councils.map(c => c.slug),
					is_comparison_export: true,
					selected_fields: selectedFields.map(f => f.slug),
					selected_years: selectedYears.map(y => y.label || y),
				}),
			});

			if (data.success) {
				showNotification(`List "${listName}" created successfully`, 'success');
				return data.list;
			} else {
				throw new Error(data.message || 'Failed to create list');
			}
		} catch (err) {
			showNotification(`Failed to create list: ${err.message}`, 'error');
			throw err;
		} finally {
			setLoading(false);
		}
	}, [config.apiUrls.saveAsList, apiCall, councils, selectedFields, selectedYears, showNotification]);

	/**
	 * Export comparison data in specified format
	 */
	const exportData = useCallback(async (format = 'csv') => {
		try {
			setLoading(true);
			const response = await fetch(config.apiUrls.exportData, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': config.csrfToken,
				},
				body: JSON.stringify({
					councils: councils.map(c => c.slug),
					fields: selectedFields.map(f => f.slug),
					years: selectedYears.map(y => y.label || y),
					format: format,
				}),
			});

			if (!response.ok) {
				throw new Error(`Export failed: ${response.statusText}`);
			}

			// Handle file download
			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `council-comparison-${new Date().toISOString().split('T')[0]}.${format}`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			showNotification(`Data exported as ${format.toUpperCase()}`, 'success');
		} catch (err) {
			showNotification(`Export failed: ${err.message}`, 'error');
		} finally {
			setLoading(false);
		}
	}, [config.apiUrls.exportData, config.csrfToken, councils, selectedFields, selectedYears, showNotification]);

	// Expose function to open comparison (called from header basket)  
	useEffect(() => {
		if (onComparisonToggle) {
			// Mark React app as mounted
			const root = document.getElementById('comparison-basket-react-root');
			if (root) {
				root.setAttribute('data-react-mounted', 'true');
				console.log('✅ ComparisonBasketApp mounted successfully');
			}

			// Make toggle function available globally
			window.openComparison = () => {
				console.log(`🛒 openComparison called with ${councils.length} councils`);
				
				if (councils.length === 0) {
					showNotification('Your comparison basket is empty. Add councils to compare by visiting council pages.', 'warning');
				} else if (councils.length === 1) {
					showNotification('Please add another council to compare', 'warning');
				} else {
					console.log('🚀 Showing comparison overlay');
					setShowComparison(true);
				}
			};
		}
		return () => {
			if (window.openComparison) {
				delete window.openComparison;
			}
		};
	}, [councils.length, onComparisonToggle, showNotification]);

	// Auto-show comparison overlay when page loads with sufficient councils
	useEffect(() => {
		// Only auto-show if we're on the comparison page and have enough councils
		if (onComparisonToggle && councils.length >= 2) {
			// Small delay to ensure UI is ready
			const timer = setTimeout(() => {
				console.log('🚀 Auto-showing comparison overlay on page load');
				setShowComparison(true);
			}, 100);

			return () => clearTimeout(timer);
		}
	}, [onComparisonToggle, councils.length]);

	// Choose drag & drop backend based on device
	const dndBackend = isMobile ? TouchBackend : HTML5Backend;
	const dndOptions = isMobile ? { enableMouseEvents: true } : {};

	return (
		<ErrorBoundary>
			<div id="comparison-basket-app" className="comparison-basket-app">
				{/* Notification Display */}
				{notification && (
					<div id="comparison-notification" className={`fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg animate-slide-in ${
						notification.type === 'success' 
							? 'bg-green-50 border border-green-200 text-green-800'
							: notification.type === 'warning'
							? 'bg-yellow-50 border border-yellow-200 text-yellow-800'
							: 'bg-red-50 border border-red-200 text-red-800'
					}`}>
						<div className="flex items-start">
							<div className="flex-shrink-0 mr-3">
								{notification.type === 'success' && (
									<svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
									</svg>
								)}
								{notification.type === 'warning' && (
									<svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
										<path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
									</svg>
								)}
								{notification.type === 'error' && (
									<svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
										<path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
									</svg>
								)}
							</div>
							<div className="flex-1 text-sm">
								{notification.message}
							</div>
							<button 
								onClick={() => setNotification(null)}
								className="ml-3 text-gray-400 hover:text-gray-600 transition-colors"
							>
								<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						</div>
					</div>
				)}

				{/* Loading Overlay */}
				{loading && <LoadingSpinner />}

				{/* Error Display */}
				{error && (
					<div id="comparison-error-display" className="bg-red-50 border border-red-200 rounded-lg p-4 m-6">
						<div className="flex items-start">
							<svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
								<path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
							</svg>
							<div className="text-sm text-red-800">
								<strong>Error:</strong> {error}
							</div>
						</div>
					</div>
				)}

				{/* Simple Clean Interface */}
				{councils.length === 0 ? (
					<div className="min-h-screen flex items-center justify-center bg-gray-50">
						<div className="text-center max-w-md mx-auto px-6">
							<svg className="w-20 h-20 text-gray-300 mx-auto mb-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13v6a2 2 0 002 2h6a2 2 0 002-2v-6M7 13H5.4" />
							</svg>
							<h1 className="text-2xl font-bold text-gray-900 mb-4">Council Comparison</h1>
							<p className="text-lg text-gray-600 mb-8">
								Add councils to your comparison basket to get started. You can compare up to {config.maxCouncils} councils side-by-side.
							</p>
							<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
								<div className="flex items-start">
									<svg className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
										<path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
									</svg>
									<div className="text-sm text-blue-800">
										<strong>How to get started:</strong> Go to any council page and click "Add to comparison" to build your basket.
									</div>
								</div>
							</div>
						</div>
					</div>
				) : (
					<>
						{/* Comparison Interface */}
						{showComparison && (
							<SimpleComparison 
								councils={councils}
								selectedFields={selectedFields}
								selectedYears={selectedYears}
								availableFields={config.availableFields}
								availableYears={config.availableYears}
								onFieldsChange={setSelectedFields}
								onYearsChange={setSelectedYears}
								onClose={() => setShowComparison(false)}
								apiUrls={config.apiUrls}
								csrfToken={config.csrfToken}
							/>
						)}
					</>
				)}
			</div>
		</ErrorBoundary>
	);
};

export default ComparisonBasketApp;