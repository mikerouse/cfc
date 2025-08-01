import React, { useState, useEffect } from 'react';
import SimpleComparison from './SimpleComparison';

/**
 * Global comparison overlay that can be invoked from any page
 * Lightweight wrapper that loads data on demand
 */
const GlobalComparison = () => {
	const [isOpen, setIsOpen] = useState(false);
	const [councils, setCouncils] = useState([]);
	const [selectedFields, setSelectedFields] = useState([]);
	const [selectedYears, setSelectedYears] = useState([]);
	const [availableFields, setAvailableFields] = useState([]);
	const [availableYears, setAvailableYears] = useState([]);
	const [loading, setLoading] = useState(false);

	// Make global function available
	useEffect(() => {
		// Small delay to ensure component is ready
		const timer = setTimeout(() => {
			window.openGlobalComparison = () => {
				setIsOpen(true);
				loadInitialData();
			};
		}, 100);

		return () => {
			clearTimeout(timer);
			if (window.openGlobalComparison) {
				delete window.openGlobalComparison;
			}
		};
	}, []);

	const loadInitialData = async () => {
		if (loading) return;
		
		setLoading(true);
		try {
			// Load basket data, available fields, and years in parallel
			const [basketResponse, fieldsResponse, yearsResponse] = await Promise.all([
				fetch('/api/comparison/basket/'),
				fetch('/api/comparison/fields/'),
				fetch('/api/comparison/years/')
			]);

			if (basketResponse.ok) {
				const basketData = await basketResponse.json();
				setCouncils(basketData.councils || []);
			}

			if (fieldsResponse.ok) {
				const fieldsData = await fieldsResponse.json();
				setAvailableFields(fieldsData.fields || []);
			}

			if (yearsResponse.ok) {
				const yearsData = await yearsResponse.json();
				setAvailableYears(yearsData.years || []);
				
				// Default to latest year
				if (yearsData.years && yearsData.years.length > 0 && selectedYears.length === 0) {
					setSelectedYears([yearsData.years[0]]);
				}
			}

		} catch (error) {
			console.error('Failed to load comparison data:', error);
		} finally {
			setLoading(false);
		}
	};

	const handleClose = () => {
		setIsOpen(false);
	};

	const getCsrfToken = () => {
		return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
			   document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
	};

	if (!isOpen) return null;

	// Show empty state if no councils
	if (councils.length === 0) {
		return (
			<div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
				<div className="bg-white rounded-lg shadow-xl max-w-md mx-4 p-6">
					<div className="flex items-center justify-between mb-4">
						<h2 className="text-xl font-bold text-gray-900">Comparison Basket</h2>
						<button
							onClick={handleClose}
							className="text-gray-400 hover:text-gray-600 transition-colors"
						>
							<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
					
					<div className="text-center py-8">
						<svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13v6a2 2 0 002 2h6a2 2 0 002-2v-6M7 13H5.4" />
						</svg>
						<h3 className="text-lg font-medium text-gray-900 mb-2">Your comparison basket is empty</h3>
						<p className="text-gray-600 mb-6">
							Visit any council page and click "Add to Comparison" to start comparing councils.
						</p>
						<button
							onClick={handleClose}
							className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
						>
							Close
						</button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<SimpleComparison 
			councils={councils}
			selectedFields={selectedFields}
			selectedYears={selectedYears}
			availableFields={availableFields}
			availableYears={availableYears}
			onFieldsChange={setSelectedFields}
			onYearsChange={setSelectedYears}
			onClose={handleClose}
			apiUrls={{
				getFieldData: '/api/comparison/fields/',
				getYearData: '/api/comparison/years/',
				exportData: '/api/comparison/export/',
			}}
			csrfToken={getCsrfToken()}
		/>
	);
};

export default GlobalComparison;