import React, { useState } from 'react';

/**
 * Modal for saving comparison basket as a custom list
 */
const SaveAsListModal = ({ councils, onClose, onSave }) => {
	const [formData, setFormData] = useState({
		name: `Comparison of ${councils.length} councils`,
		description: '',
	});
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const handleSubmit = async (e) => {
		e.preventDefault();
		
		if (!formData.name.trim()) {
			setError('List name is required');
			return;
		}

		try {
			setLoading(true);
			setError(null);
			
			await onSave(formData.name.trim(), formData.description.trim());
			onClose();
		} catch (err) {
			setError(err.message || 'Failed to save list');
		} finally {
			setLoading(false);
		}
	};

	const handleInputChange = (e) => {
		setFormData({
			...formData,
			[e.target.name]: e.target.value,
		});
		// Clear error when user starts typing
		if (error) setError(null);
	};

	return (
		<div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
			<div className="relative top-20 mx-auto p-5 border max-w-md w-full shadow-lg rounded-md bg-white">
				<div className="mt-3">
					{/* Header */}
					<div className="flex items-center justify-between mb-6">
						<div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
							<svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
							</svg>
						</div>
						<button
							onClick={onClose}
							disabled={loading}
							className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
						>
							<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>

					<h3 className="text-lg font-medium text-gray-900 text-center mb-6">
						Save Comparison as List
					</h3>

					{/* Council Preview */}
					<div className="mb-6 p-4 bg-gray-50 rounded-lg">
						<h4 className="text-sm font-medium text-gray-700 mb-2">
							Councils to include ({councils.length}):
						</h4>
						<div className="space-y-1 max-h-32 overflow-y-auto">
							{councils.map((council, index) => (
								<div key={council.slug} className="flex items-center text-sm text-gray-600">
									<span className="w-6 text-gray-400">#{index + 1}</span>
									<span className="flex-1">{council.name}</span>
								</div>
							))}
						</div>
					</div>

					{/* Form */}
					<form onSubmit={handleSubmit}>
						{/* Error Display */}
						{error && (
							<div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
								<div className="flex items-start">
									<svg className="w-5 h-5 text-red-500 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
										<path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
									</svg>
									<div className="text-sm text-red-800">
										{error}
									</div>
								</div>
							</div>
						)}

						{/* List Name */}
						<div className="mb-4">
							<label htmlFor="list-name" className="block text-sm font-medium text-gray-700 mb-2">
								List Name <span className="text-red-500">*</span>
							</label>
							<input
								type="text"
								id="list-name"
								name="name"
								value={formData.name}
								onChange={handleInputChange}
								required
								disabled={loading}
								className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
								placeholder="Enter a name for your list"
								maxLength="100"
							/>
						</div>

						{/* Description */}
						<div className="mb-6">
							<label htmlFor="list-description" className="block text-sm font-medium text-gray-700 mb-2">
								Description (optional)
							</label>
							<textarea
								id="list-description"
								name="description"
								value={formData.description}
								onChange={handleInputChange}
								disabled={loading}
								rows={3}
								className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
								placeholder="Add a description for your list"
								maxLength="500"
							/>
						</div>

						{/* Actions */}
						<div className="flex flex-col sm:flex-row gap-3">
							<button
								type="button"
								onClick={onClose}
								disabled={loading}
								className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 transition-colors"
							>
								Cancel
							</button>
							<button
								type="submit"
								disabled={loading || !formData.name.trim()}
								className="flex-1 px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
							>
								{loading ? (
									<>
										<svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" fill="none" viewBox="0 0 24 24">
											<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
											<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										Saving...
									</>
								) : (
									<>
										<svg className="w-4 h-4 inline-block mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
											<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
										</svg>
										Save List
									</>
								)}
							</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	);
};

export default SaveAsListModal;