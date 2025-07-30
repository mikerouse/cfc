import React, { useState } from 'react';
import { useDrag, useDrop } from 'react-dnd';

/**
 * Individual council card component with drag-and-drop capability
 */
const CouncilCard = ({ 
  council, 
  onRemove, 
  onAddToList, 
  lists = [], 
  showRemoveButton = false,
  isDraggable = true,
  listId = null,
  onMove = null
}) => {
  const [showActions, setShowActions] = useState(false);

  // Drag and drop setup
  const [{ isDragging }, drag] = useDrag({
    type: 'council',
    item: { 
      slug: council.slug, 
      name: council.name,
      fromListId: listId
    },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    canDrag: isDraggable,
  });

  const [{ isOver }, drop] = useDrop({
    accept: 'council',
    drop: (item) => {
      if (onMove && item.fromListId !== listId && item.slug !== council.slug) {
        onMove(item.slug, item.fromListId, listId);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  const opacity = isDragging ? 0.5 : 1;

  return (
    <div
      ref={isDraggable ? (node) => drag(drop(node)) : drop}
      className={`
        p-4 transition-all duration-200 cursor-${isDraggable ? 'move' : 'default'}
        ${isDragging ? 'opacity-50' : ''}
        ${isOver ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'}
      `}
      style={{ opacity }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex items-start gap-3">
        {/* Drag Handle (Mobile/Touch) */}
        {isDraggable && (
          <div className="flex-shrink-0 touch-manipulation">
            <div className="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </div>
          </div>
        )}

        {/* Council Logo */}
        <div className="flex-shrink-0">
          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-lg shadow-sm overflow-hidden bg-gray-100 flex items-center justify-center">
            {council.logo_url ? (
              <img 
                src={council.logo_url} 
                alt={council.name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H5m14 0a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10" />
              </svg>
            )}
          </div>
        </div>

        {/* Council Information */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 text-sm sm:text-base leading-tight mb-1">
            <a 
              href={`/councils/${council.slug}/`} 
              className="hover:text-blue-600 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              {council.name}
            </a>
          </h3>
          
          <div className="text-xs sm:text-sm text-gray-600 space-y-1">
            {council.type && (
              <div className="flex items-center">
                <svg className="w-3 h-3 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H5m14 0a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10" />
                </svg>
                {council.type}
              </div>
            )}
            {council.nation && (
              <div className="flex items-center">
                <svg className="w-3 h-3 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {council.nation}
              </div>
            )}
            {council.population && (
              <div className="flex items-center">
                <svg className="w-3 h-3 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Population: {parseInt(council.population).toLocaleString()}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className={`flex-shrink-0 transition-opacity duration-200 ${showActions || 'sm:opacity-0 sm:group-hover:opacity-100'}`}>
          <div className="flex flex-col gap-2 min-w-0">
            {/* Add to List Dropdown */}
            {lists.length > 0 && onAddToList && (
              <select 
                className="text-xs border border-gray-300 rounded-md px-2 py-1 min-w-[100px]"
                onChange={(e) => {
                  if (e.target.value) {
                    onAddToList(e.target.value, council.slug);
                    e.target.value = '';
                  }
                }}
              >
                <option value="">Add to list...</option>
                {lists.map(list => (
                  <option key={list.id} value={list.id}>
                    {list.name}
                  </option>
                ))}
              </select>
            )}

            {/* Remove Button */}
            {showRemoveButton && onRemove && (
              <button
                onClick={() => onRemove()}
                className="inline-flex items-center justify-center px-2 py-1 text-xs font-medium rounded-md text-red-700 bg-red-50 border border-red-300 hover:bg-red-100 transition-colors min-h-[28px]"
                title="Remove from list"
              >
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Remove
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Drag Drop Visual Indicator */}
      {isDraggable && (
        <div className="mt-2 text-xs text-gray-500 flex items-center">
          <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
          </svg>
          Drag to move between lists
        </div>
      )}
    </div>
  );
};

export default CouncilCard;