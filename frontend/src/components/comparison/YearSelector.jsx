import React from 'react';

/**
 * Year selector component for choosing which time periods to compare
 */
const YearSelector = ({ availableYears, selectedYears, onYearsChange }) => {
	const handleYearToggle = (year) => {
		const isSelected = selectedYears.some(y => (y.label || y) === (year.label || year));
		
		if (isSelected) {
			// Remove year
			onYearsChange(selectedYears.filter(y => (y.label || y) !== (year.label || year)));
		} else {
			// Add year
			onYearsChange([...selectedYears, year]);
		}
	};

	const handleSelectAll = () => {
		onYearsChange(availableYears);
	};

	const handleClearAll = () => {
		onYearsChange([]);
	};

	const handleSelectRecent = () => {
		// Select the 3 most recent years
		const recentYears = availableYears.slice(-3);
		onYearsChange(recentYears);
	};

	return (
		<div id="comparison-year-selector" className="space-y-4">
			{/* Header */}
			<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
				<div>
					<h3 className="text-lg font-medium text-gray-900">
						Select Years to Compare
					</h3>
					<p className="text-sm text-gray-500">
						Choose the time periods for cross-year comparison
					</p>
				</div>
				<div className="flex items-center gap-2">
					<span className="text-sm text-gray-500">
						{selectedYears.length} selected
					</span>
					{selectedYears.length > 0 && (
						<button
							onClick={handleClearAll}
							className="text-sm text-red-600 hover:text-red-800 font-medium"
						>
							Clear all
						</button>
					)}
				</div>
			</div>

			{/* Quick Actions */}
			<div className="flex flex-wrap gap-2">
				<button
					onClick={handleSelectRecent}
					className="px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					Recent 3 Years
				</button>
				<button
					onClick={handleSelectAll}
					className="px-3 py-1 text-sm font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-500"
				>
					All Years ({availableYears.length})
				</button>
			</div>

			{/* Selected Years Summary */}
			{selectedYears.length > 0 && (
				<div className="bg-green-50 border border-green-200 rounded-lg p-4">
					<h4 className="text-sm font-medium text-green-900 mb-2">
						Selected Years ({selectedYears.length}):
					</h4>
					<div className="flex flex-wrap gap-2">
						{selectedYears
							.sort((a, b) => (b.label || b).localeCompare(a.label || a))
							.map(year => (
								<span
									key={year.label || year}
									className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
								>
									{year.label || year}
									<button
										onClick={() => handleYearToggle(year)}
										className="ml-2 text-green-600 hover:text-green-800"
										title="Remove year"
									>
										<svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</span>
							))}
					</div>
				</div>
			)}

			{/* Available Years */}
			<div className="border border-gray-200 rounded-lg">
				{availableYears.length === 0 ? (
					<div className="p-8 text-center">
						<svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
						</svg>
						<h3 className="text-lg font-medium text-gray-900 mb-2">No years available</h3>
						<p className="text-gray-500">
							No data years are available for comparison
						</p>
					</div>
				) : (
					<div className="p-4">
						<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
							{availableYears
								.sort((a, b) => (b.label || b).localeCompare(a.label || a))
								.map(year => {
									const isSelected = selectedYears.some(y => (y.label || y) === (year.label || year));
									const yearLabel = year.label || year;
									
									return (
										<label
											key={yearLabel}
											className={`flex items-center justify-center p-3 border-2 rounded-lg cursor-pointer transition-all duration-200 ${
												isSelected
													? 'border-green-500 bg-green-50 text-green-800'
													: 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
											}`}
										>
											<input
												type="checkbox"
												checked={isSelected}
												onChange={() => handleYearToggle(year)}
												className="sr-only"
											/>
											<div className="text-center">
												<div className="text-sm font-medium">
													{yearLabel}
												</div>
												{year.data_count && (
													<div className="text-xs text-gray-500 mt-1">
														{year.data_count} fields
													</div>
												)}
											</div>
											{isSelected && (
												<svg className="w-4 h-4 text-green-600 absolute top-1 right-1" fill="currentColor" viewBox="0 0 20 20">
													<path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
												</svg>
											)}
										</label>
									);
								})}
						</div>
					</div>
				)}
			</div>

			{/* Comparison Tips */}
			{selectedYears.length > 1 && (
				<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
					<div className="flex items-start">
						<svg className="w-5 h-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
							<path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
						</svg>
						<div className="text-sm text-yellow-800">
							<strong>Cross-year comparison selected:</strong> Data will be shown for each year side-by-side. This is useful for tracking trends and changes over time.
						</div>
					</div>
				</div>
			)}

			{/* Usage Tips */}
			<div className="bg-gray-50 rounded-lg p-4">
				<h4 className="text-sm font-medium text-gray-900 mb-2">
					📅 Tips for selecting years:
				</h4>
				<ul className="text-sm text-gray-600 space-y-1">
					<li>• Select 1 year for simple comparison across councils</li>
					<li>• Select 2-3 years to see trends and changes over time</li>
					<li>• Use "Recent 3 Years" for the most current data</li>
					<li>• Consider data availability - some councils may have gaps</li>
				</ul>
			</div>
		</div>
	);
};

export default YearSelector;