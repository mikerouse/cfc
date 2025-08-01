import React, { useState, useEffect } from 'react';

/**
 * Simple, intuitive comparison interface - Apple/GOV.UK style
 * Horizontal scrolling grid with obvious field add/remove
 */
const SimpleComparison = ({ 
	councils, 
	selectedFields, 
	selectedYears,
	availableFields = [],
	availableYears = [],
	onFieldsChange,
	onYearsChange,
	onClose,
	apiUrls,
	csrfToken 
}) => {
	const [comparisonData, setComparisonData] = useState({});
	const [loading, setLoading] = useState(false);
	const [showFieldSelector, setShowFieldSelector] = useState(false);
	const [showYearSelector, setShowYearSelector] = useState(false);

	// Load comparison data when fields/years change
	useEffect(() => {
		if (councils.length > 0 && selectedFields.length > 0 && selectedYears.length > 0) {
			loadComparisonData();
		}
	}, [councils, selectedFields, selectedYears]);

	const loadComparisonData = async () => {
		setLoading(true);
		try {
			const response = await fetch('/api/comparison/data/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken,
				},
				body: JSON.stringify({
					councils: councils.map(c => c.slug),
					fields: selectedFields.map(f => f.slug),
					years: selectedYears.map(y => y.label || y),
				}),
			});
			
			if (response.ok) {
				const data = await response.json();
				setComparisonData(data.data || {});
			}
		} catch (error) {
			console.error('Failed to load comparison data:', error);
		} finally {
			setLoading(false);
		}
	};

	const addField = (field) => {
		if (!selectedFields.find(f => f.slug === field.slug)) {
			onFieldsChange([...selectedFields, field]);
		}
		setShowFieldSelector(false);
	};

	const removeField = (fieldSlug) => {
		onFieldsChange(selectedFields.filter(f => f.slug !== fieldSlug));
	};

	const addYear = (year) => {
		if (!selectedYears.find(y => (y.id || y) === (year.id || year))) {
			onYearsChange([...selectedYears, year]);
		}
		setShowYearSelector(false);
	};

	const removeYear = (yearId) => {
		onYearsChange(selectedYears.filter(y => (y.id || y) !== yearId));
	};

	const formatValue = (value) => {
		if (value === null || value === undefined || value === '') return 'No data';
		if (typeof value === 'number') {
			return value.toLocaleString();
		}
		return value;
	};

	return (
		<div className="fixed inset-0 bg-white z-40 overflow-hidden">
			{/* Header */}
			<div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold text-gray-900">
						Compare {councils.length} Council{councils.length === 1 ? '' : 's'}
					</h1>
					<p className="text-sm text-gray-600 mt-1">
						{selectedFields.length} characteristic{selectedFields.length === 1 ? '' : 's'} • {selectedYears.length} year{selectedYears.length === 1 ? '' : 's'}
					</p>
				</div>
				<button
					onClick={onClose}
					className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
					aria-label="Close comparison"
				>
					<svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			{/* Field and Year Controls */}
			<div className="bg-gray-50 border-b border-gray-200 px-6 py-3">
				<div className="flex items-center justify-between">
					<div className="flex items-center space-x-4">
						<button
							onClick={() => setShowFieldSelector(!showFieldSelector)}
							className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
						>
							<svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
							</svg>
							Add Field
						</button>
					
						{selectedFields.length > 0 && (
							<div className="flex items-center space-x-2">
								<span className="text-sm text-gray-600">Fields:</span>
								{selectedFields.map(field => (
									<span
										key={field.slug}
										className="inline-flex items-center bg-white border border-gray-200 rounded-full px-3 py-1 text-sm"
									>
										{field.name}
										<button
											onClick={() => removeField(field.slug)}
											className="ml-2 text-gray-400 hover:text-red-600 transition-colors"
										>
											<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									</span>
								))}
							</div>
						)}
					</div>

					{/* Year Controls */}
					<div className="flex items-center space-x-4">
						<button
							onClick={() => setShowYearSelector(!showYearSelector)}
							className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
						>
							<svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
							</svg>
							{selectedYears.length > 0 ? `${selectedYears.length} Year${selectedYears.length === 1 ? '' : 's'}` : 'Add Year'}
						</button>

						{selectedYears.length > 0 && (
							<div className="flex items-center space-x-2">
								<span className="text-sm text-gray-600">Years:</span>
								{selectedYears.map(year => (
									<span
										key={year.id || year}
										className="inline-flex items-center bg-white border border-gray-200 rounded-full px-3 py-1 text-sm"
									>
										{year.label || year}
										<button
											onClick={() => removeYear(year.id || year)}
											className="ml-2 text-gray-400 hover:text-red-600 transition-colors"
										>
											<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									</span>
								))}
							</div>
						)}
					</div>
				</div>

				{/* Field Selector Dropdown */}
				{showFieldSelector && (
					<div className="absolute mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
						<div className="p-3 border-b border-gray-200">
							<h3 className="font-medium text-gray-900">Choose fields to compare</h3>
						</div>
						<div className="max-h-60 overflow-y-auto">
							{availableFields
								.filter(field => !selectedFields.find(f => f.slug === field.slug))
								.map(field => (
									<button
										key={field.slug}
										onClick={() => addField(field)}
										className="w-full text-left px-3 py-2 hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0"
									>
										<div className="font-medium text-gray-900">{field.name}</div>
										{field.description && (
											<div className="text-sm text-gray-600 mt-1">{field.description}</div>
										)}
									</button>
								))
							}
						</div>
					</div>
				)}

				{/* Year Selector Dropdown */}
				{showYearSelector && (
					<div className="absolute right-6 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
						<div className="p-3 border-b border-gray-200">
							<h3 className="font-medium text-gray-900">Choose years to compare</h3>
						</div>
						<div className="max-h-60 overflow-y-auto">
							{availableYears
								.filter(year => !selectedYears.find(y => (y.id || y) === (year.id || year)))
								.map(year => (
									<button
										key={year.id || year}
										onClick={() => addYear(year)}
										className="w-full text-left px-3 py-2 hover:bg-green-50 transition-colors border-b border-gray-100 last:border-b-0"
									>
										<div className="font-medium text-gray-900">{year.label || year}</div>
										{year.start_date && year.end_date && (
											<div className="text-sm text-gray-600 mt-1">
												{new Date(year.start_date).toLocaleDateString()} - {new Date(year.end_date).toLocaleDateString()}
											</div>
										)}
									</button>
								))
							}
						</div>
					</div>
				)}
			</div>

			{/* Comparison Grid - Apple/GOV.UK style horizontal scrolling */}
			<div className="flex-1 overflow-hidden">
				{loading ? (
					<div className="flex items-center justify-center h-64">
						<div className="text-center">
							<div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
							<p className="text-gray-600">Loading comparison data...</p>
						</div>
					</div>
				) : selectedFields.length === 0 ? (
					<div className="flex items-center justify-center h-64">
						<div className="text-center max-w-md mx-auto px-6">
							<svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
							</svg>
							<h3 className="text-xl font-semibold text-gray-900 mb-2">Choose fields to compare</h3>
							<p className="text-gray-600">Click "Add Field" above to start comparing data across your {councils.length} selected councils</p>
						</div>
					</div>
				) : (
					<div className="h-full flex flex-col">
						{/* Horizontal scrolling container */}
						<div className="flex-1 overflow-x-auto overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
							<div className="min-w-full">
								{/* Clean grid layout - councils as columns for easier horizontal scrolling */}
								<div className="grid gap-6 p-6" style={{ gridTemplateColumns: `repeat(${councils.length}, minmax(280px, 1fr))` }}>
									{councils.map(council => (
										<div key={council.slug} className="bg-white border border-gray-200 rounded-lg shadow-sm">
											{/* Council header */}
											<div className="bg-blue-50 border-b border-gray-200 px-4 py-3 rounded-t-lg">
												<h3 className="font-semibold text-gray-900">{council.name}</h3>
												<p className="text-sm text-gray-600">
													{council.council_type?.name} • {council.council_nation?.name}
												</p>
											</div>
											
											{/* Council data */}
											<div className="p-4 space-y-4">
												{selectedFields.map(field => (
													<div key={field.slug} className="border-b border-gray-100 pb-3 last:border-b-0 last:pb-0">
														<div className="text-sm font-medium text-gray-700 mb-1">
															{field.name}
														</div>
														{selectedYears.map(year => (
															<div key={year.label || year} className="text-lg font-semibold text-gray-900">
																{formatValue(comparisonData[council.slug]?.[field.slug]?.[year.label || year]?.value)}
																{selectedYears.length > 1 && (
																	<span className="text-sm text-gray-500 font-normal ml-2">({year.label || year})</span>
																)}
															</div>
														))}
													</div>
												))}
											</div>
										</div>
									))}
								</div>
							</div>
						</div>
						
						{/* Horizontal scroll indicator */}
						{councils.length > 3 && (
							<div className="bg-gray-50 border-t border-gray-200 px-6 py-2 text-center">
								<p className="text-sm text-gray-600 flex items-center justify-center">
									<svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
									</svg>
									Scroll horizontally to see all councils
									<svg className="w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
									</svg>
								</p>
							</div>
						)}
					</div>
				)}
			</div>
		</div>
	);
};

export default SimpleComparison;