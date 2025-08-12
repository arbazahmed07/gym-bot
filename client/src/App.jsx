import React, { useState } from 'react'
import './App.css'
import VideoUpload from './components/VideoUpload'
import ChatUI from './components/ChatUI'
import AnalysisResults from './components/AnalysisResults'

function App() {
  const [analysisResults, setAnalysisResults] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleAnalysisComplete = (results) => {
    setAnalysisResults(results)
    setIsAnalyzing(false)
  }

  const handleAnalysisStart = () => {
    setIsAnalyzing(true)
    setAnalysisResults(null)
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <h1 className="text-4xl font-bold text-center text-gray-800 mb-8">
          AI Gym Form Analyzer
        </h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Video Upload and Results */}
          <div className="space-y-6">
            <VideoUpload 
              onAnalysisStart={handleAnalysisStart}
              onAnalysisComplete={handleAnalysisComplete}
              isAnalyzing={isAnalyzing}
            />
            
            {analysisResults && (
              <AnalysisResults results={analysisResults} />
            )}
          </div>
          
          {/* Right Column - Chat UI */}
          <div>
            <ChatUI analysisResults={analysisResults} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
