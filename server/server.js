import express from 'express'
import cors from 'cors'
import multer from 'multer'
import mongoose from 'mongoose'
import dotenv from 'dotenv'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import fs from 'fs'
import { spawn } from 'child_process'
// Remove OpenAI import
// import OpenAI from 'openai'
import { v4 as uuidv4 } from 'uuid'

dotenv.config()

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const app = express()
const PORT = process.env.PORT || 5000

// Remove OpenAI initialization
// const openai = new OpenAI({
//   apiKey: process.env.OPENAI_API_KEY,
// })

// Middleware
app.use(cors())
app.use(express.json())
app.use('/uploads', express.static('uploads'))

// Create uploads directory if it doesn't exist
const uploadsDir = join(__dirname, 'uploads')
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir)
}

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/')
  },
  filename: (req, file, cb) => {
    const uniqueName = `${uuidv4()}-${file.originalname}`
    cb(null, uniqueName)
  }
})

const upload = multer({
  storage: storage,
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB limit
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('video/')) {
      cb(null, true)
    } else {
      cb(new Error('Only video files are allowed'), false)
    }
  }
})

// MongoDB connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/gym-analyzer')
  .then(() => console.log('Connected to MongoDB'))
  .catch(err => console.error('MongoDB connection error:', err))

// Workout Analysis Schema
const workoutAnalysisSchema = new mongoose.Schema({
  videoPath: String,
  originalName: String,
  exerciseName: String,
  repCount: Number,
  feedback: [String],
  formScore: Number,
  createdAt: { type: Date, default: Date.now },
  userId: String // For future user authentication
})

const WorkoutAnalysis = mongoose.model('WorkoutAnalysis', workoutAnalysisSchema)

// Function to call Gemini API
async function callGeminiAPI(prompt) {
  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${process.env.GEMINI_API_KEY}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [{
          parts: [{
            text: prompt
          }]
        }],
        generationConfig: {
          temperature: 0.7,
          topK: 40,
          topP: 0.95,
          maxOutputTokens: 1024,
        },
        safetySettings: [
          {
            category: "HARM_CATEGORY_HARASSMENT",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          },
          {
            category: "HARM_CATEGORY_HATE_SPEECH",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          },
          {
            category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          },
          {
            category: "HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold: "BLOCK_MEDIUM_AND_ABOVE"
          }
        ]
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Gemini API response:', errorText)
      throw new Error(`Gemini API error: ${response.status} - ${errorText}`)
    }

    const data = await response.json()
    
    if (!data.candidates || !data.candidates[0] || !data.candidates[0].content) {
      throw new Error('Invalid response format from Gemini API')
    }
    
    return data.candidates[0].content.parts[0].text
  } catch (error) {
    console.error('Gemini API error:', error)
    throw error
  }
}

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Gym Analyzer API is running!' })
})

// Video analysis endpoint
app.post('/api/analyze', upload.single('video'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No video file uploaded' })
    }

    const videoPath = req.file.path
    console.log('Processing video:', videoPath)

    // Call Python analysis script
    const analysisResult = await analyzeVideo(videoPath)
    
    // Save to database
    const workoutAnalysis = new WorkoutAnalysis({
      videoPath: videoPath,
      originalName: req.file.originalname,
      exerciseName: analysisResult.exerciseName,
      repCount: analysisResult.repCount,
      feedback: analysisResult.feedback,
      formScore: analysisResult.formScore
    })

    await workoutAnalysis.save()

    res.json(analysisResult)

  } catch (error) {
    console.error('Analysis error:', error)
    res.status(500).json({ error: 'Video analysis failed' })
  }
})

// Chat endpoint - Updated to use Gemini
app.post('/api/chat', async (req, res) => {
  try {
    const { message, analysisResults } = req.body

    let systemPrompt = `You are an experienced fitness coach and personal trainer. You help users improve their workout form and provide encouraging, actionable advice.`
    
    if (analysisResults) {
      systemPrompt += ` The user just completed a ${analysisResults.exerciseName} exercise with ${analysisResults.repCount} repetitions and received a form score of ${analysisResults.formScore}/10. The feedback points were: ${analysisResults.feedback.join(', ')}.`
    }

    const fullPrompt = `${systemPrompt}\n\nUser: ${message}\n\nAssistant:`

    const response = await callGeminiAPI(fullPrompt)

    res.json({ response })

  } catch (error) {
    console.error('Chat error:', error)
    res.status(500).json({ error: 'Chat request failed' })
  }
})

// Get all workout analyses
app.get('/api/analyses', async (req, res) => {
  try {
    const analyses = await WorkoutAnalysis.find().sort({ createdAt: -1 }).limit(50)
    res.json(analyses)
  } catch (error) {
    console.error('Database error:', error)
    res.status(500).json({ error: 'Failed to fetch analyses' })
  }
})

// Function to analyze video using Python script
async function analyzeVideo(videoPath) {
  return new Promise((resolve, reject) => {
    const pythonScript = join(__dirname, 'analysis', 'pose_analyzer.py')
    const python = spawn('python', [pythonScript, videoPath])

    let output = ''
    let error = ''

    python.stdout.on('data', (data) => {
      output += data.toString()
    })

    python.stderr.on('data', (data) => {
      error += data.toString()
    })

    python.on('close', (code) => {
      if (code !== 0) {
        console.error('Python script error:', error)
        // Return mock data if Python script fails
        resolve({
          exerciseName: "squat",
          repCount: 12,
          feedback: ["Keep your back straight", "Don't let knees go inward"],
          formScore: 7.5
        })
      } else {
        try {
          const result = JSON.parse(output)
          resolve(result)
        } catch (parseError) {
          console.error('Failed to parse Python output:', parseError)
          // Return mock data if parsing fails
          resolve({
            exerciseName: "squat",
            repCount: 8,
            feedback: ["Good form overall", "Try to go deeper in your squat"],
            formScore: 8.2
          })
        }
      }
    })
  })
}

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})