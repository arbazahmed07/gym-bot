import React, { useState, useRef } from 'react'

const VideoUpload = ({ onAnalysisStart, onAnalysisComplete, isAnalyzing }) => {
  const [selectedFile, setSelectedFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (file.type.startsWith('video/')) {
        setSelectedFile(file)
      } else {
        alert('Please select a video file')
      }
    }
  }

  const handleChange = (e) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (file.type.startsWith('video/')) {
        setSelectedFile(file)
      } else {
        alert('Please select a video file')
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedFile) return

    onAnalysisStart()

    const formData = new FormData()
    formData.append('video', selectedFile)

    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Analysis failed')
      }

      const results = await response.json()
      onAnalysisComplete(results)
    } catch (error) {
      console.error('Error analyzing video:', error)
      alert('Error analyzing video. Please try again.')
      onAnalysisComplete(null)
    }
  }

  const onButtonClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-semibold mb-4 text-gray-800">Upload Workout Video</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          className={`relative border-2 border-dashed rounded-lg p-6 text-center ${
            dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
          } ${isAnalyzing ? 'opacity-50 pointer-events-none' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleChange}
            className="hidden"
            disabled={isAnalyzing}
          />
          
          {selectedFile ? (
            <div className="space-y-2">
              <div className="text-sm text-green-600">✓ File selected:</div>
              <div className="font-medium text-gray-800">{selectedFile.name}</div>
              <div className="text-sm text-gray-500">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-gray-600">
                Drag and drop your workout video here, or
              </div>
              <button
                type="button"
                onClick={onButtonClick}
                className="text-blue-600 hover:text-blue-800 font-medium"
                disabled={isAnalyzing}
              >
                click to browse
              </button>
              <div className="text-sm text-gray-500">
                Supports MP4, MOV, AVI (max 100MB)
              </div>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={!selectedFile || isAnalyzing}
          className={`w-full py-3 px-6 rounded-lg font-medium ${
            !selectedFile || isAnalyzing
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isAnalyzing ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Analyzing Video...</span>
            </div>
          ) : (
            'Analyze Workout Form'
          )}
        </button>
      </form>
    </div>
  )
}

export default VideoUpload