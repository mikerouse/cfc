import React, { useState } from 'react';

/**
 * Field selector component for choosing which characteristics to compare
 */
const FieldSelector = ({ availableFields, selectedFields, onFieldsChange }) => {
	const [searchTerm, setSearchTerm] = useState('');
	const [selectedCategory, setSelectedCategory] = useState('all');

	// Group fields by category
	const fieldsByCategory = availableFields.reduce((acc, field) => {
		const category = field.category || 'other';
		if (!acc[category]) {
			acc[category] = [];
		}
		acc[category].push(field);
		return acc;
	}, {});

	const categories = Object.keys(fieldsByCategory).sort();

	// Filter fields based on search and category
	const filteredFields = availableFields.filter(field => {
		const matchesSearch = field.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
							 field.description?.toLowerCase().includes(searchTerm.toLowerCase());
		const matchesCategory = selectedCategory === 'all' || field.category === selectedCategory;
		return matchesSearch && matchesCategory;
	});

	const handleFieldToggle = (field) => {
		const isSelected = selectedFields.some(f => f.slug === field.slug);
		
		if (isSelected) {
			// Remove field
			onFieldsChange(selectedFields.filter(f => f.slug !== field.slug));
		} else {
			// Add field
			onFieldsChange([...selectedFields, field]);
		}
	};

	const handleSelectAll = () => {
		onFieldsChange(filteredFields);
	};

	const handleClearAll = () => {
		onFieldsChange([]);
	};

	return (
		<div id="comparison-field-selector" className="space-y-4">
			{/* Header */}
			<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
				<div>
					<h3 className="text-lg font-medium text-gray-900">
						Select Characteristics to Compare
					</h3>
					<p className="text-sm text-gray-500">
						Choose the data fields you want to compare across councils
					</p>
				</div>
				<div className="flex items-center gap-2">
					<span className="text-sm text-gray-500">
						{selectedFields.length} selected
					</span>
					{selectedFields.length > 0 && (
						<button
							onClick={handleClearAll}
							className="text-sm text-red-600 hover:text-red-800 font-medium"
						>
							Clear all
						</button>
					)}
				</div>
			</div>

			{/* Search and Filter Controls */}
			<div className="flex flex-col sm:flex-row gap-4">
				{/* Search */}
				<div className="flex-1">
					<div className="relative">
						<svg className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
						<input
							type="text"
							placeholder="Search characteristics..."
							value={searchTerm}
							onChange={(e) => setSearchTerm(e.target.value)}
							className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
						/>
					</div>
				</div>

				{/* Category Filter */}
				<div className="sm:w-48">
					<select
						value={selectedCategory}
						onChange={(e) => setSelectedCategory(e.target.value)}
						className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
					>
						<option value="all">All Categories</option>
						{categories.map(category => (
							<option key={category} value={category}>
								{category.charAt(0).toUpperCase() + category.slice(1)}
							</option>
						))}
					</select>
				</div>

				{/* Quick Actions */}
				{filteredFields.length > 0 && (
					<button
						onClick={handleSelectAll}
						className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						Select All ({filteredFields.length})
					</button>
				)}
			</div>

			{/* Selected Fields Summary */}
			{selectedFields.length > 0 && (
				<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
					<h4 className="text-sm font-medium text-blue-900 mb-2">
						Selected Characteristics ({selectedFields.length}):
					</h4>
					<div className="flex flex-wrap gap-2">
						{selectedFields.map(field => (
							<span
								key={field.slug}
								className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
							>
								{field.name}
								<button
									onClick={() => handleFieldToggle(field)}
									className="ml-2 text-blue-600 hover:text-blue-800"
									title="Remove field"
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

			{/* Available Fields */}
			<div className="border border-gray-200 rounded-lg max-h-96 overflow-y-auto">
				{filteredFields.length === 0 ? (
					<div className="p-8 text-center">
						<svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
						<h3 className="text-lg font-medium text-gray-900 mb-2">No fields found</h3>
						<p className="text-gray-500">
							{searchTerm || selectedCategory !== 'all' 
								? 'Try adjusting your search or filter criteria'
								: 'No characteristics available'
							}
						</p>
					</div>
				) : (
					<div className="divide-y divide-gray-200">
						{filteredFields.map(field => {
							const isSelected = selectedFields.some(f => f.slug === field.slug);
							
							return (
								<label
									key={field.slug}
									className={`flex items-start p-4 cursor-pointer hover:bg-gray-50 ${
										isSelected ? 'bg-blue-50' : ''
									}`}
								>
									<input
										type="checkbox"
										checked={isSelected}
										onChange={() => handleFieldToggle(field)}
										className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
									/>
									<div className="ml-3 flex-1">
										<div className="flex items-center justify-between">
											<h4 className="text-sm font-medium text-gray-900">
												{field.name}
											</h4>
											{field.category && (
												<span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600">
													{field.category}
												</span>
											)}
										</div>
										{field.description && (
											<p className="text-sm text-gray-500 mt-1">
												{field.description}
											</p>
										)}
										<div className="flex items-center mt-2 text-xs text-gray-400">
											{field.data_type && (
												<span className="mr-4">
													Type: {field.data_type}
												</span>
											)}
											{field.unit && (
												<span>
													Unit: {field.unit}
												</span>
											)}
										</div>
									</div>
								</label>
							);
						})}
					</div>
				)}
			</div>

			{/* Usage Tips */}
			<div className="bg-gray-50 rounded-lg p-4">
				<h4 className="text-sm font-medium text-gray-900 mb-2">
					💡 Tips for selecting characteristics:
				</h4>
				<ul className="text-sm text-gray-600 space-y-1">
					<li>• Choose 3-8 characteristics for the clearest comparison</li>
					<li>• Mix different categories to get a comprehensive view</li>
					<li>• Consider selecting both absolute values and per-capita figures</li>
					<li>• Use search to quickly find specific financial metrics</li>
				</ul>
			</div>
		</div>
	);
};

export default FieldSelector;