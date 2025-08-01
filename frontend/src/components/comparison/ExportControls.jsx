import React, { useState } from 'react';
import SaveAsListModal from './SaveAsListModal';

/**
 * Export controls component for comparison data
 * Provides CSV/JSON export and save as list functionality
 */
const ExportControls = ({ 
	councils, 
	selectedFields, 
	selectedYears, 
	onExport, 
	onSaveAsList 
}) => {
	const [showSaveModal, setShowSaveModal] = useState(false);
	const [isExporting, setIsExporting] = useState(false);

	const handleExport = async (format) => {
		setIsExporting(true);
		try {
			await onExport(format);
		} finally {
			setIsExporting(false);
		}
	};

	const generateShareUrl = () => {
		const params = new URLSearchParams({
			councils: councils.map(c => c.slug).join(','),
			fields: selectedFields.map(f => f.slug).join(','),
			years: selectedYears.map(y => y.label || y).join(','),
		});
		
		return `${window.location.origin}/compare/?${params.toString()}`;
	};

	const handleShare = async () => {
		const shareUrl = generateShareUrl();
		
		if (navigator.share) {
			// Use Web Share API if available
			try {
				await navigator.share({
					title: 'Council Finance Comparison',
					text: `Compare ${councils.length} councils across ${selectedFields.length} characteristics`,
					url: shareUrl,
				});
			} catch (err) {
				// User cancelled or error occurred, fall back to clipboard
				copyToClipboard(shareUrl);
			}
		} else {
			// Fall back to clipboard copy
			copyToClipboard(shareUrl);
		}
	};

	const copyToClipboard = async (text) => {
		try {
			await navigator.clipboard.writeText(text);
			// You could show a toast notification here
			alert('Share link copied to clipboard!');
		} catch (err) {
			// Fall back to older method
			const textArea = document.createElement('textarea');
			textArea.value = text;
			document.body.appendChild(textArea);
			textArea.select();
			document.execCommand('copy');
			document.body.removeChild(textArea);
			alert('Share link copied to clipboard!');
		}
	};

	const canExport = councils.length > 0 && selectedFields.length > 0 && selectedYears.length > 0;

	return (
		<div id="comparison-export-controls" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
			<div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
				{/* Export Summary */}
				<div className="flex-1">
					<h3 className="text-lg font-semibold text-gray-900 mb-2">
						Export & Share Comparison
					</h3>
					<p className="text-gray-600 mb-4">
						{canExport ? (
							<>
								Ready to export comparison of <strong>{councils.length} councils</strong> across{' '}
								<strong>{selectedFields.length} characteristics</strong> for{' '}
								<strong>{selectedYears.length} year{selectedYears.length !== 1 ? 's' : ''}</strong>.
							</>
						) : (
							'Select councils, characteristics, and years to enable export options.'
						)}
					</p>

					{/* Export Stats */}
					{canExport && (
						<div className="grid grid-cols-3 gap-4 text-center bg-gray-50 rounded-lg p-4">
							<div>
								<div className="text-2xl font-bold text-blue-600">{councils.length}</div>
								<div className="text-sm text-gray-500">Councils</div>
							</div>
							<div>
								<div className="text-2xl font-bold text-green-600">{selectedFields.length}</div>
								<div className="text-sm text-gray-500">Characteristics</div>
							</div>
							<div>
								<div className="text-2xl font-bold text-purple-600">{selectedYears.length}</div>
								<div className="text-sm text-gray-500">Year{selectedYears.length !== 1 ? 's' : ''}</div>
							</div>
						</div>
					)}
				</div>

				{/* Action Buttons */}
				<div className="flex flex-col sm:flex-row gap-3 lg:flex-col lg:w-64">
					{/* Save as List */}
					<button
						onClick={() => setShowSaveModal(true)}
						disabled={councils.length === 0}
						className="inline-flex items-center justify-center px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						<svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
						</svg>
						Save as List
					</button>

					{/* Export Options */}
					<div className="flex gap-2">
						<button
							onClick={() => handleExport('csv')}
							disabled={!canExport || isExporting}
							className="flex-1 inline-flex items-center justify-center px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
						>
							{isExporting ? (
								<svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
									<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
									<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
							) : (
								<svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
							)}
							Export CSV
						</button>

						<button
							onClick={() => handleExport('json')}
							disabled={!canExport || isExporting}
							className="flex-1 inline-flex items-center justify-center px-4 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
						>
							{isExporting ? (
								<svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-600" fill="none" viewBox="0 0 24 24">
									<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
									<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
							) : (
								<svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
							)}
							Export JSON
						</button>
					</div>

					{/* Share Button */}
					<button
						onClick={handleShare}
						disabled={!canExport}
						className="inline-flex items-center justify-center px-6 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						<svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
						</svg>
						Share Comparison
					</button>
				</div>
			</div>

			{/* Export Format Info */}
			{canExport && (
				<div className="mt-6 pt-6 border-t border-gray-200">
					<h4 className="text-sm font-medium text-gray-900 mb-3">Export Format Information:</h4>
					<div className="grid md:grid-cols-2 gap-4 text-sm text-gray-600">
						<div className="flex items-start">
							<div className="flex-shrink-0 w-12 h-8 bg-green-100 rounded flex items-center justify-center mr-3">
								<span className="text-green-600 font-mono text-xs">CSV</span>
							</div>
							<div>
								<div className="font-medium text-gray-700">Comma-Separated Values</div>
								<div className="text-xs">Perfect for Excel, Google Sheets, and data analysis</div>
							</div>
						</div>
						<div className="flex items-start">
							<div className="flex-shrink-0 w-12 h-8 bg-blue-100 rounded flex items-center justify-center mr-3">
								<span className="text-blue-600 font-mono text-xs">JSON</span>
							</div>
							<div>
								<div className="font-medium text-gray-700">JavaScript Object Notation</div>
								<div className="text-xs">Ideal for developers and API integration</div>
							</div>
						</div>
					</div>
				</div>
			)}

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

export default ExportControls;