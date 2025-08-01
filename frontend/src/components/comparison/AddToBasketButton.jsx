import React, { useState, useEffect } from 'react';

/**
 * Add to Basket button for council pages - Apple/GOV.UK style
 * Simple, obvious button that adds councils to comparison basket
 */
const AddToBasketButton = ({ councilSlug, councilName, className = '' }) => {
	const [isInBasket, setIsInBasket] = useState(false);
	const [basketCount, setBasketCount] = useState(0);
	const [loading, setLoading] = useState(false);

	// Check if council is already in basket on component load
	useEffect(() => {
		checkBasketStatus();
	}, [councilSlug]);

	const checkBasketStatus = async () => {
		try {
			const response = await fetch('/api/comparison/basket/');
			if (response.ok) {
				const data = await response.json();
				const councils = data.councils || [];
				setBasketCount(councils.length);
				setIsInBasket(councils.some(c => c.slug === councilSlug));
			}
		} catch (error) {
			console.error('Failed to check basket status:', error);
		}
	};

	const addToBasket = async () => {
		if (loading || isInBasket) return;

		setLoading(true);
		try {
			const response = await fetch(`/compare/add/${councilSlug}/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': getCsrfToken(),
					'Content-Type': 'application/x-www-form-urlencoded',
				},
			});

			if (response.ok) {
				const data = await response.json();
				if (data.success) {
					setIsInBasket(true);
					setBasketCount(prev => prev + 1);
					
					// Show success notification
					showNotification(`${councilName} added to comparison basket`, 'success');
				} else {
					showNotification(data.message || 'Failed to add to basket', 'error');
				}
			}
		} catch (error) {
			console.error('Failed to add to basket:', error);
			showNotification('Failed to add to basket', 'error');
		} finally {
			setLoading(false);
		}
	};

	const removeFromBasket = async () => {
		if (loading || !isInBasket) return;

		setLoading(true);
		try {
			const response = await fetch(`/compare/remove/${councilSlug}/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': getCsrfToken(),
					'Content-Type': 'application/x-www-form-urlencoded',
				},
			});

			if (response.ok) {
				const data = await response.json();
				if (data.success) {
					setIsInBasket(false);
					setBasketCount(prev => Math.max(0, prev - 1));
					showNotification('Removed from comparison basket', 'success');
				}
			}
		} catch (error) {
			console.error('Failed to remove from basket:', error);
			showNotification('Failed to remove from basket', 'error');
		} finally {
			setLoading(false);
		}
	};

	const viewComparison = () => {
		window.location.href = '/compare/';
	};

	const getCsrfToken = () => {
		return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
			   document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
	};

	const showNotification = (message, type) => {
		// Simple notification - you could integrate with your main notification system
		const notification = document.createElement('div');
		notification.className = `fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg animate-slide-in ${
			type === 'success' 
				? 'bg-green-50 border border-green-200 text-green-800'
				: 'bg-red-50 border border-red-200 text-red-800'
		}`;
		notification.innerHTML = `
			<div class="flex items-start">
				<div class="flex-shrink-0 mr-3">
					${type === 'success' 
						? '<svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>'
						: '<svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>'
					}
				</div>
				<div class="text-sm">${message}</div>
			</div>
		`;
		document.body.appendChild(notification);
		setTimeout(() => {
			document.body.removeChild(notification);
		}, 4000);
	};

	if (isInBasket) {
		return (
			<div className={`inline-flex items-center space-x-2 ${className}`}>
				<button
					onClick={removeFromBasket}
					disabled={loading}
					className="inline-flex items-center px-4 py-2 bg-green-100 text-green-800 border border-green-200 rounded-lg hover:bg-green-200 transition-colors disabled:opacity-50"
				>
					<svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
						<path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
					</svg>
					In Basket
				</button>
				
				{basketCount > 1 && (
					<button
						onClick={viewComparison}
						className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
					>
						Compare {basketCount} Councils
						<svg className="w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
						</svg>
					</button>
				)}
			</div>
		);
	}

	return (
		<button
			onClick={addToBasket}
			disabled={loading}
			className={`
				inline-flex items-center px-4 py-2 
				bg-blue-600 text-white rounded-lg 
				hover:bg-blue-700 active:bg-blue-800
				transition-colors duration-200 
				disabled:opacity-50 disabled:cursor-not-allowed
				font-medium shadow-sm hover:shadow-md
				${className}
			`}
		>
			{loading ? (
				<>
					<div className="animate-spin w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full"></div>
					Adding...
				</>
			) : (
				<>
					<svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
					</svg>
					Add to Comparison
				</>
			)}
		</button>
	);
};

export default AddToBasketButton;