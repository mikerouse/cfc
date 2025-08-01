import React from 'react';

/**
 * Header component for the comparison basket
 * Shows current status, view mode toggle, and main actions
 */
const BasketHeader = ({ 
	councilCount, 
	maxCouncils, 
	viewMode, 
	onViewModeChange, 
	onClearBasket 
}) => {
	return (
		<div id="comparison-basket-header" className="bg-white border-b border-gray-200">
			<div className="px-4 sm:px-6 lg:px-8 py-6">
				{/* Title and Status */}
				<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
					<div className="mb-4 sm:mb-0">
						<h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
							🛒 Council Comparison Basket
						</h1>
						<p className="text-gray-600">
							{councilCount === 0 
								? 'Your comparison basket is empty'
								: `${councilCount} of ${maxCouncils} councils selected`
							}
						</p>
					</div>

					{/* Action Buttons */}
					{councilCount > 0 && (
						<div className="flex flex-col sm:flex-row gap-3">
							<button
								onClick={onClearBasket}
								className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
							>
								Clear Basket
							</button>
						</div>
					)}
				</div>

				{/* View Mode Toggle */}
				{councilCount > 0 && (
					<div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
						<button
							onClick={() => onViewModeChange('basket')}
							className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
								viewMode === 'basket'
									? 'bg-white text-gray-900 shadow-sm'
									: 'text-gray-500 hover:text-gray-700'
							}`}
						>
							<svg className="w-4 h-4 inline-block mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 012-2m0 0V5a2 2 0 012-2h4a2 2 0 012 2v2M7 7h10" />
							</svg>
							Basket View
						</button>
						<button
							onClick={() => onViewModeChange('compare')}
							className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
								viewMode === 'compare'
									? 'bg-white text-gray-900 shadow-sm'
									: 'text-gray-500 hover:text-gray-700'
							}`}
						>
							<svg className="w-4 h-4 inline-block mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
							</svg>
							Comparison Table
						</button>
					</div>
				)}

				{/* Progress Bar */}
				{councilCount > 0 && (
					<div className="mt-4">
						<div className="flex items-center justify-between text-xs text-gray-500 mb-1">
							<span>Basket capacity</span>
							<span>{councilCount}/{maxCouncils}</span>
						</div>
						<div className="w-full bg-gray-200 rounded-full h-2">
							<div 
								className="bg-blue-600 h-2 rounded-full transition-all duration-300"
								style={{ width: `${(councilCount / maxCouncils) * 100}%` }}
							></div>
						</div>
					</div>
				)}
			</div>
		</div>
	);
};

export default BasketHeader;