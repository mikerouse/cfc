import React, { useState, useCallback, useRef } from 'react';

/**
 * PDF Upload and Processing Component
 * 
 * Handles:
 * 1. PDF file upload or URL input
 * 2. Processing status display
 * 3. Error handling and retry logic
 */
const PDFUploadProcessor = ({
  councilData,
  selectedYear,
  csrfToken,
  onProcessingComplete,
  onBack,
  className = ""
}) => {
  const [uploadMethod, setUploadMethod] = useState('upload'); // 'upload' or 'url'
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState('');
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);

  // Processing stages for user feedback
  const stages = [
    { key: 'upload', label: 'Uploading PDF', icon: '📤' },
    { key: 'extract', label: 'Extracting text with Tika', icon: '📄' },
    { key: 'analyze', label: 'AI analysis in progress', icon: '🤖' },
    { key: 'map', label: 'Mapping to database fields', icon: '🗂️' },
    { key: 'complete', label: 'Processing complete', icon: '✅' }
  ];

  const handleFileSelect = useCallback((event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        setError('Please select a PDF file');
        return;
      }
      if (selectedFile.size > 50 * 1024 * 1024) { // 50MB limit
        setError('File size must be less than 50MB');
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (droppedFile.type !== 'application/pdf') {
        setError('Please drop a PDF file');
        return;
      }
      if (droppedFile.size > 50 * 1024 * 1024) {
        setError('File size must be less than 50MB');
        return;
      }
      setFile(droppedFile);
      setError(null);
    }
  }, []);

  const processPDF = useCallback(async () => {
    console.log('🔄 PDF Processing Started');
    console.log('📊 Council:', councilData);
    console.log('📅 Year:', selectedYear);
    console.log('📤 Upload Method:', uploadMethod);
    
    if (uploadMethod === 'upload' && file) {
      console.log('📄 File Details:', {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: new Date(file.lastModified)
      });
    } else if (uploadMethod === 'url') {
      console.log('🔗 PDF URL:', fileUrl);
    }

    setProcessing(true);
    setError(null);
    setProgress(0);

    try {
      // Stage 1: Upload/Submit
      console.log('📤 Stage 1: Starting upload/submit');
      setProcessingStage('upload');
      setProgress(10);
      
      const formData = new FormData();
      formData.append('council_slug', councilData.slug);
      formData.append('year_id', selectedYear.id);
      
      if (uploadMethod === 'upload' && file) {
        formData.append('pdf_file', file);
        formData.append('source_type', 'upload');
        console.log('📎 Attached file to FormData');
      } else if (uploadMethod === 'url' && fileUrl) {
        formData.append('pdf_url', fileUrl);
        formData.append('source_type', 'url');
        console.log('🔗 Added URL to FormData');
      }

      // Log FormData contents
      console.log('📋 FormData contents:');
      for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(`  ${key}: File(${value.name}, ${value.size} bytes)`);
        } else {
          console.log(`  ${key}: ${value}`);
        }
      }

      // Stage 2: Extract text with Tika
      console.log('📄 Stage 2: Starting text extraction');
      setProcessingStage('extract');
      setProgress(30);
      
      const startTime = Date.now();
      console.log('🌐 Sending request to /api/council/process-pdf/');
      
      const response = await fetch('/api/council/process-pdf/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken
        },
        body: formData
      });
      
      const requestTime = Date.now() - startTime;
      console.log(`⏱️ Request completed in ${requestTime}ms`);
      console.log('📡 Response status:', response.status, response.statusText);

      if (!response.ok) {
        console.error('❌ Response not OK:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('📄 Error response body:', errorText);
        
        try {
          const errorData = JSON.parse(errorText);
          throw new Error(errorData.error || 'PDF processing failed');
        } catch (parseError) {
          console.error('❌ Failed to parse error response as JSON:', parseError);
          throw new Error(`Server error (${response.status}): ${errorText.substring(0, 200)}...`);
        }
      }

      // Stage 3: AI Analysis
      console.log('🤖 Stage 3: AI Analysis phase');
      setProcessingStage('analyze');
      setProgress(60);
      
      console.log('📄 Reading response JSON...');
      const result = await response.json();
      console.log('✅ Response JSON parsed successfully');
      console.log('📊 API Response:', result);
      
      // Check if we got extracted data
      if (result.extracted_data) {
        console.log('📈 Extracted data found:', Object.keys(result.extracted_data).length, 'fields');
        Object.entries(result.extracted_data).forEach(([fieldSlug, data]) => {
          console.log(`  📊 ${fieldSlug}:`, data);
        });
      } else {
        console.warn('⚠️ No extracted_data in response');
      }
      
      if (result.confidence_scores) {
        console.log('🎯 Confidence scores:', result.confidence_scores);
      } else {
        console.warn('⚠️ No confidence_scores in response');
      }
      
      if (result.processing_stats) {
        console.log('📈 Processing stats:', result.processing_stats);
      }
      
      // Stage 4: Field Mapping
      console.log('🗂️ Stage 4: Field mapping phase');
      setProcessingStage('map');
      setProgress(90);
      
      // Stage 5: Complete
      console.log('✅ Stage 5: Processing complete');
      setProcessingStage('complete');
      setProgress(100);
      
      // Pass extracted data to parent component for review
      console.log('🔄 Passing data to parent component...');
      setTimeout(() => {
        console.log('📤 Calling onProcessingComplete with:');
        console.log('  - extracted_data:', result.extracted_data);
        console.log('  - confidence_scores:', result.confidence_scores);
        onProcessingComplete(result.extracted_data, result.confidence_scores);
      }, 1000);
      
    } catch (error) {
      console.error('💥 PDF processing error:', error);
      console.error('📄 Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      setError(error.message || 'Failed to process PDF. Please try again.');
      setProcessing(false);
      setProcessingStage('');
    }
  }, [file, fileUrl, uploadMethod, councilData, selectedYear, csrfToken, onProcessingComplete]);

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' bytes';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className={`bg-white ${className}`}>
      <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={onBack}
            className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium mb-4"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back to method selection
          </button>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Upload Financial Statement
          </h2>
          <p className="text-gray-600">
            Upload {councilData?.name}'s financial statement for {selectedYear?.label}
          </p>
        </div>

        {!processing ? (
          <>
            {/* Upload Method Toggle */}
            <div className="mb-6">
              <div className="flex rounded-lg bg-gray-100 p-1">
                <button
                  onClick={() => setUploadMethod('upload')}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                    uploadMethod === 'upload'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Upload PDF File
                </button>
                <button
                  onClick={() => setUploadMethod('url')}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                    uploadMethod === 'url'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Provide PDF URL
                </button>
              </div>
            </div>

            {/* File Upload Area */}
            {uploadMethod === 'upload' ? (
              <div className="mb-6">
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    file ? 'border-green-300 bg-green-50' : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                >
                  {file ? (
                    <div className="space-y-2">
                      <div className="text-4xl">✅</div>
                      <p className="text-lg font-medium text-gray-900">{file.name}</p>
                      <p className="text-sm text-gray-600">{formatFileSize(file.size)}</p>
                      <button
                        onClick={() => setFile(null)}
                        className="text-sm text-red-600 hover:text-red-800 underline"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="text-4xl mb-4">📄</div>
                      <p className="text-lg font-medium text-gray-900 mb-2">
                        Drop your PDF here or click to browse
                      </p>
                      <p className="text-sm text-gray-600 mb-4">
                        Maximum file size: 50MB
                      </p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="application/pdf"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                      >
                        Select PDF File
                      </button>
                    </>
                  )}
                </div>
              </div>
            ) : (
              // URL Input
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  PDF URL
                </label>
                <input
                  type="url"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://example.com/financial-statement.pdf"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-2 text-sm text-gray-600">
                  Enter the direct URL to the PDF financial statement
                </p>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center">
                  <span className="text-red-600 mr-2">⚠️</span>
                  <p className="text-red-800">{error}</p>
                </div>
              </div>
            )}

            {/* Info Box */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">What happens next?</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• We'll extract text from your PDF using Apache Tika</li>
                <li>• AI will analyze and identify financial data</li>
                <li>• You'll review and confirm extracted values</li>
                <li>• Data will be saved to the database</li>
              </ul>
            </div>

            {/* Process Button */}
            <div className="flex justify-end space-x-4">
              <button
                onClick={onBack}
                className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={processPDF}
                disabled={
                  (uploadMethod === 'upload' && !file) ||
                  (uploadMethod === 'url' && !fileUrl)
                }
                className={`px-6 py-2 rounded-md text-white transition-colors ${
                  ((uploadMethod === 'upload' && file) || (uploadMethod === 'url' && fileUrl))
                    ? 'bg-blue-600 hover:bg-blue-700'
                    : 'bg-gray-400 cursor-not-allowed'
                }`}
              >
                Process PDF
              </button>
            </div>
          </>
        ) : (
          // Processing State
          <div className="py-8">
            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-medium text-gray-700">Processing</span>
                <span className="text-sm text-gray-600">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Processing Stages */}
            <div className="space-y-4">
              {stages.map((stage, index) => {
                const isActive = stage.key === processingStage;
                const isComplete = stages.findIndex(s => s.key === processingStage) > index;
                
                return (
                  <div
                    key={stage.key}
                    className={`flex items-center p-4 rounded-lg border ${
                      isActive ? 'border-blue-300 bg-blue-50' :
                      isComplete ? 'border-green-300 bg-green-50' :
                      'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="text-2xl mr-4">
                      {isComplete ? '✅' : stage.icon}
                    </div>
                    <div className="flex-1">
                      <p className={`font-medium ${
                        isActive ? 'text-blue-900' :
                        isComplete ? 'text-green-900' :
                        'text-gray-600'
                      }`}>
                        {stage.label}
                      </p>
                      {isActive && (
                        <p className="text-sm text-gray-600 mt-1">
                          Please wait, this may take a few moments...
                        </p>
                      )}
                    </div>
                    {isActive && (
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PDFUploadProcessor;