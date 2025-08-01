import React from 'react';

/**
 * Floating basket button - Apple/e-commerce style
 * Always visible, shows count, opens comparison on click
 */
const FloatingBasket = ({ councilCount, onClick, isActive = false }) => {
	if (councilCount === 0) return null;

	return (
		<button
			onClick={onClick}
			className={`
				fixed bottom-6 right-6 z-50
				flex items-center justify-center
				w-16 h-16 rounded-full shadow-lg
				transition-all duration-300 ease-in-out
				transform hover:scale-105 active:scale-95
				${isActive 
					? 'bg-blue-600 text-white shadow-xl' 
					: 'bg-white text-blue-600 hover:bg-blue-50 border-2 border-blue-600'
				}
			`}
			aria-label={`Compare ${councilCount} council${councilCount === 1 ? '' : 's'}`}
		>
			<div className="relative">
				{/* Basket Icon */}
				<svg 
					className="w-7 h-7" 
					fill="none" 
					viewBox="0 0 24 24" 
					stroke="currentColor"
				>
					<path 
						strokeLinecap="round" 
						strokeLinejoin="round" 
						strokeWidth={2} 
						d="M3 3h2l.4 2M7 13h10l4-8H5.4m0 0L7 13m0 0l-2.5 5M7 13v6a2 2 0 002 2h6a2 2 0 002-2v-6M7 13H5.4" 
					/>
				</svg>
				
				{/* Count Badge */}
				<span className={`
					absolute -top-2 -right-2
					w-6 h-6 rounded-full
					flex items-center justify-center
					text-xs font-bold
					${isActive 
						? 'bg-white text-blue-600' 
						: 'bg-blue-600 text-white'
					}
				`}>
					{councilCount}
				</span>
			</div>
		</button>
	);
};

export default FloatingBasket;