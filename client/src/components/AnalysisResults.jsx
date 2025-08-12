import React from 'react'

const AnalysisResults = ({ results }) => {
  if (!results) return null

  const getScoreColor = (score) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBg = (score) => {
    if (score >= 8) return 'bg-green-100'
    if (score >= 6) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-semibold mb-4 text-gray-800">Analysis Results</h2>
      
      <div className="space-y-4">
        {/* Exercise Type */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="font-medium text-gray-700">Exercise:</span>
          <span className="text-lg font-semibold text-blue-600 capitalize">
            {results.exerciseName}
          </span>
        </div>

        {/* Rep Count */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="font-medium text-gray-700">Repetitions:</span>
          <span className="text-lg font-semibold text-purple-600">
            {results.repCount}
          </span>
        </div>

        {/* Form Score */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="font-medium text-gray-700">Form Score:</span>
          <div className={`px-3 py-1 rounded-full ${getScoreBg(results.formScore)}`}>
            <span className={`text-lg font-bold ${getScoreColor(results.formScore)}`}>
              {results.formScore}/10
            </span>
          </div>
        </div>

        {/* Feedback */}
        <div className="space-y-2">
          <h3 className="font-medium text-gray-700">Form Feedback:</h3>
          <div className="space-y-2">
            {results.feedback.map((tip, index) => (
              <div
                key={index}
                className="flex items-start space-x-2 p-3 bg-orange-50 rounded-lg border-l-4 border-orange-400"
              >
                <span className="text-orange-600 mt-0.5">⚠️</span>
                <span className="text-gray-700">{tip}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AnalysisResults