import 'dotenv/config'
import cors from 'cors'
import express from 'express'
import { ensureAuthSchema, loginUser, registerUser } from './src/auth.js'
import { closePool, getDashboardData, initPool, pingDatabase } from './src/oracle.js'

const app = express()
const port = Number(process.env.PORT) || 4000

app.use(cors())
app.use(express.json())

app.get('/api/health', async (_req, res) => {
  try {
    const ok = await pingDatabase()
    res.json({ ok })
  } catch (error) {
    res.status(500).json({
      ok: false,
      message: 'Oracle connection failed',
      details: error.message,
    })
  }
})

app.get('/api/dashboard', async (req, res) => {
  try {
    const limit = req.query.limit
    const payload = await getDashboardData(limit)
    res.json(payload)
  } catch (error) {
    res.status(500).json({
      message: 'Failed to fetch dashboard data from Oracle',
      details: error.message,
    })
  }
})

app.post('/api/auth/register', registerUser)
app.post('/api/auth/login', loginUser)

const start = async () => {
  try {
    await initPool()
    await ensureAuthSchema()
    app.listen(port, () => {
      console.log(`Oracle API server running at http://localhost:${port}`)
    })
  } catch (error) {
    console.error('Unable to start Oracle API server:', error.message)
    process.exit(1)
  }
}

const shutdown = async () => {
  try {
    await closePool()
  } finally {
    process.exit(0)
  }
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)

start()
