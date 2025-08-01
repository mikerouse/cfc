import React, { useState } from 'react';
import { useDrag, useDrop } from 'react-dnd';
import SaveAsListModal from './SaveAsListModal';

/**
 * Council basket view showing selected councils as cards
 * Supports drag-and-drop reordering
 */
const CouncilBasket = ({ 
	councils, 
	onRemoveCouncil, 
	onReorderCouncils, 
	onSaveAsList, 
	maxCouncils 
}) => {
	const [showSaveModal, setShowSaveModal] = useState(false);

	if (councils.length === 0) {
		return <EmptyBasketState />;
	}

	return (
		<div id="comparison-council-basket" className="px-4 sm:px-6 lg:px-8 py-6">
			{/* Controls */}
			<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
				<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
					<div className="flex items-center gap-2">
						<span className="text-sm font-medium text-gray-700">
							{councils.length} council{councils.length !== 1 ? 's' : ''} selected
						</span>
						{councils.length === maxCouncils && (
							<span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
								Maximum reached
							</span>
						)}
					</div>
					<div className="flex items-center gap-2">
						<button
							onClick={() => setShowSaveModal(true)}
							className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
						>
							<svg className="w-4 h-4 inline-block mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
							</svg>
							Save as List
						</button>
					</div>
				</div>
			</div>

			{/* Council Cards Grid */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				{councils.map((council, index) => (
					<DraggableCouncilCard
						key={council.slug}
						council={council}
						index={index}
						onRemove={onRemoveCouncil}
						onReorder={onReorderCouncils}
					/>
				))}
			</div>

			{/* Save as List Modal */}
			{showSaveModal && (
				<SaveAsListModal
					councils={councils}
					onClose={() => setShowSaveModal(false)}
					onSave={onSaveAsList}
				/>
			)}
		</div>
	);
};

/**
 * Draggable council card component
 */
const DraggableCouncilCard = ({ council, index, onRemove, onReorder }) => {
	const [{ isDragging }, drag] = useDrag({
		type: 'council-card',
		item: { index },
		collect: (monitor) => ({
			isDragging: monitor.isDragging(),
		}),
	});

	const [, drop] = useDrop({
		accept: 'council-card',
		hover: (draggedItem) => {
			if (draggedItem.index !== index) {
				onReorder(draggedItem.index, index);
				draggedItem.index = index;
			}
		},
	});

	return (
		<div
			ref={(node) => drag(drop(node))}
			className={`council-card bg-white rounded-lg shadow-sm border border-gray-200 p-6 cursor-move transition-all duration-200 ${
				isDragging ? 'opacity-50 rotate-2 scale-105' : 'hover:shadow-md hover:border-gray-300'
			}`}
		>
			{/* Drag Handle */}
			<div className="flex items-center justify-between mb-4">
				<div className="flex items-center text-gray-400">
					<svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
					</svg>
					<span className="text-xs font-medium">Drag to reorder</span>
				</div>
				<button
					onClick={() => onRemove(council.slug)}
					className="text-red-400 hover:text-red-600 p-1 rounded-md hover:bg-red-50 transition-colors"
					title="Remove from basket"
				>
					<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			{/* Council Info */}
			<div className="flex-1">
				<h3 className="text-lg font-semibold text-gray-900 mb-1">
					{council.name}
				</h3>
				<p className="text-sm text-gray-500 mb-4">
					{council.council_type?.name || 'Council'}
				</p>

				{/* Council Details */}
				<div className="space-y-2 mb-4">
					{council.council_nation && (
						<div className="flex items-center text-sm text-gray-600">
							<svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
							</svg>
							{council.council_nation.name}
						</div>
					)}

					{council.population && (
						<div className="flex items-center text-sm text-gray-600">
							<svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
							</svg>
							Population: {council.population?.toLocaleString() || 'Unknown'}
						</div>
					)}

					{council.latest_year && (
						<div className="flex items-center text-sm text-gray-600">
							<svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
							</svg>
							Latest data: {council.latest_year}
						</div>
					)}
				</div>

				{/* Action */}
				<div className="flex items-center justify-between">
					<a
						href={`/councils/${council.slug}/`}
						className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center transition-colors"
					>
						View Details
						<svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
						</svg>
					</a>
					<span className="text-xs text-gray-400 font-medium">
						#{index + 1}
					</span>
				</div>
			</div>
		</div>
	);
};

/**
 * Empty state when no councils are selected
 */
const EmptyBasketState = () => {
	return (
		<div id="comparison-empty-state" className="text-center py-16 px-4">
			<div className="mx-auto h-24 w-24 text-gray-400 mb-6">
				<svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.293 2.293a1 1 0 000 1.414L6 18h12M7 13v8a2 2 0 002 2h6a2 2 0 002-2v-8" />
				</svg>
			</div>
			<h3 className="text-xl font-medium text-gray-900 mb-2">
				Your comparison basket is empty
			</h3>
			<p className="text-gray-500 mb-8 max-w-md mx-auto">
				Add councils to your basket from council pages to start comparing their financial data and characteristics. You can add up to 6 councils.
			</p>
			<div className="flex flex-col sm:flex-row gap-4 justify-center">
				<a
					href="/councils/"
					className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
				>
					<svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
					Browse Councils
				</a>
				<a
					href="/"
					className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
				>
					<svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
					</svg>
					Go Home
				</a>
			</div>
		</div>
	);
};

export default CouncilBasket;