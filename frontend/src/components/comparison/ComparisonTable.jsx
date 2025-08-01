import React, { useState, useEffect, useCallback } from 'react';
import { useDrag, useDrop } from 'react-dnd';
import FieldSelector from './FieldSelector';
import YearSelector from './YearSelector';

/**
 * Main comparison table component with drag-and-drop functionality
 * Displays councils in columns and selected fields in rows
 */
const ComparisonTable = ({
	councils,
	selectedFields,
	selectedYears,
	availableFields,
	availableYears,
	onFieldsChange,
	onYearsChange,
	onReorderCouncils,
	onReorderFields,
	apiUrls,
	csrfToken
}) => {
	const [tableData, setTableData] = useState({});
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	/**
	 * Fetch comparison data from API
	 */
	const fetchComparisonData = useCallback(async () => {
		if (councils.length === 0 || selectedFields.length === 0 || selectedYears.length === 0) {
			setTableData({});
			return;
		}

		try {
			setLoading(true);
			setError(null);

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

			if (!response.ok) {
				throw new Error(`Failed to fetch comparison data: ${response.statusText}`);
			}

			const data = await response.json();
			setTableData(data.data || {});
		} catch (err) {
			console.error('Failed to fetch comparison data:', err);
			setError(err.message);
		} finally {
			setLoading(false);
		}
	}, [councils, selectedFields, selectedYears, csrfToken]);

	// Fetch data when dependencies change
	useEffect(() => {
		fetchComparisonData();
	}, [fetchComparisonData]);

	if (councils.length === 0) {
		return (
			<div className="px-4 sm:px-6 lg:px-8 py-6">
				<div className="text-center py-12">
					<h3 className="text-lg font-medium text-gray-900 mb-2">
						No councils to compare
					</h3>
					<p className="text-gray-500">
						Add councils to your basket to start comparing their data.
					</p>
				</div>
			</div>
		);
	}

	return (
		<div id="comparison-table-container" className="px-4 sm:px-6 lg:px-8 py-6">
			{/* Controls */}
			<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
				<div className="space-y-6">
					{/* Field Selection */}
					<FieldSelector
						availableFields={availableFields}
						selectedFields={selectedFields}
						onFieldsChange={onFieldsChange}
					/>

					{/* Year Selection */}
					<YearSelector
						availableYears={availableYears}
						selectedYears={selectedYears}
						onYearsChange={onYearsChange}
					/>
				</div>
			</div>

			{/* Comparison Table */}
			{selectedFields.length > 0 && selectedYears.length > 0 ? (
				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
					{loading && (
						<div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10">
							<div className="flex items-center">
								<svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
									<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
									<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								Loading comparison data...
							</div>
						</div>
					)}

					{error && (
						<div className="p-4 bg-red-50 border-b border-red-200">
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

					<div className="overflow-x-auto">
						<table className="min-w-full divide-y divide-gray-200">
							{/* Table Header */}
							<thead className="bg-gray-50">
								<tr>
									<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 z-10">
										<div className="flex items-center">
											<svg className="w-4 h-4 mr-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
											</svg>
											Characteristic
										</div>
									</th>
									{councils.map((council, index) => (
										<DraggableColumnHeader
											key={council.slug}
											council={council}
											index={index}
											onReorder={onReorderCouncils}
										/>
									))}
								</tr>
							</thead>

							{/* Table Body */}
							<tbody className="bg-white divide-y divide-gray-200">
								{selectedFields.map((field, fieldIndex) => (
									<DraggableTableRow
										key={field.slug}
										field={field}
										fieldIndex={fieldIndex}
										councils={councils}
										selectedYears={selectedYears}
										tableData={tableData}
										onReorder={onReorderFields}
									/>
								))}
							</tbody>
						</table>
					</div>
				</div>
			) : (
				<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
					<div className="text-center">
						<svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
						</svg>
						<h3 className="text-lg font-medium text-gray-900 mb-2">
							Select fields and years to compare
						</h3>
						<p className="text-gray-500">
							Choose the characteristics and time periods you want to compare across your selected councils.
						</p>
					</div>
				</div>
			)}
		</div>
	);
};

/**
 * Draggable column header for councils
 */
const DraggableColumnHeader = ({ council, index, onReorder }) => {
	const [{ isDragging }, drag] = useDrag({
		type: 'council-column',
		item: { index },
		collect: (monitor) => ({
			isDragging: monitor.isDragging(),
		}),
	});

	const [, drop] = useDrop({
		accept: 'council-column',
		hover: (draggedItem) => {
			if (draggedItem.index !== index) {
				onReorder(draggedItem.index, index);
				draggedItem.index = index;
			}
		},
	});

	return (
		<th
			ref={(node) => drag(drop(node))}
			className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-move ${
				isDragging ? 'opacity-50' : ''
			}`}
		>
			<div className="flex flex-col">
				<div className="flex items-center mb-1">
					<svg className="w-3 h-3 mr-1 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
					</svg>
					<span className="font-semibold text-gray-900 normal-case">
						{council.name}
					</span>
				</div>
				<span className="text-gray-400 normal-case font-normal">
					{council.council_type?.name || 'Council'}
				</span>
			</div>
		</th>
	);
};

/**
 * Draggable table row for fields
 */
const DraggableTableRow = ({ field, fieldIndex, councils, selectedYears, tableData, onReorder }) => {
	const [{ isDragging }, drag] = useDrag({
		type: 'field-row',
		item: { index: fieldIndex },
		collect: (monitor) => ({
			isDragging: monitor.isDragging(),
		}),
	});

	const [, drop] = useDrop({
		accept: 'field-row',
		hover: (draggedItem) => {
			if (draggedItem.index !== fieldIndex) {
				onReorder(draggedItem.index, fieldIndex);
				draggedItem.index = fieldIndex;
			}
		},
	});

	return (
		<tr
			ref={(node) => drag(drop(node))}
			className={`cursor-move ${isDragging ? 'opacity-50' : 'hover:bg-gray-50'}`}
		>
			{/* Field Name */}
			<td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white z-10">
				<div className="flex items-center">
					<svg className="w-4 h-4 mr-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
					</svg>
					<div>
						<div className="font-medium text-gray-900">{field.name}</div>
						{field.description && (
							<div className="text-xs text-gray-500 mt-1">{field.description}</div>
						)}
					</div>
				</div>
			</td>

			{/* Council Data Cells */}
			{councils.map((council) => (
				<td key={council.slug} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
					<div className="space-y-1">
						{selectedYears.map((year) => (
							<ComparisonDataCell
								key={`${council.slug}-${field.slug}-${year.label || year}`}
								council={council}
								field={field}
								year={year}
								data={tableData[council.slug]?.[field.slug]?.[year.label || year]}
								showYear={selectedYears.length > 1}
							/>
						))}
					</div>
				</td>
			))}
		</tr>
	);
};

/**
 * Individual data cell component
 */
const ComparisonDataCell = ({ council, field, year, data, showYear }) => {
	if (data === undefined || data === null) {
		return (
			<div className="text-gray-400 text-xs">
				{showYear && <div className="font-medium">{year.label || year}</div>}
				<div>No data</div>
			</div>
		);
	}

	// Format the value based on field type
	const formatValue = (value, field) => {
		if (value === null || value === undefined) return 'N/A';
		
		if (field.data_type === 'currency') {
			return new Intl.NumberFormat('en-GB', {
				style: 'currency',
				currency: 'GBP',
				minimumFractionDigits: 0,
				maximumFractionDigits: 0,
			}).format(value);
		}
		
		if (field.data_type === 'percentage') {
			return `${parseFloat(value).toFixed(1)}%`;
		}
		
		if (field.data_type === 'number') {
			return new Intl.NumberFormat('en-GB').format(value);
		}
		
		return value.toString();
	};

	return (
		<div className="text-sm">
			{showYear && (
				<div className="text-xs font-medium text-gray-500 mb-1">
					{year.label || year}
				</div>
			)}
			<div className="font-medium">
				{formatValue(data.value, field)}
			</div>
			{data.per_capita && (
				<div className="text-xs text-gray-500">
					{formatValue(data.per_capita, { ...field, data_type: 'currency' })} per capita
				</div>
			)}
		</div>
	);
};

export default ComparisonTable;