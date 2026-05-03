import 'dotenv/config'
import oracledb from 'oracledb'

oracledb.outFormat = oracledb.OUT_FORMAT_OBJECT

const initOracleClient = () => {
  if (!process.env.ORACLE_CLIENT_LIB_DIR || oracledb.thin === false) {
    return
  }

  oracledb.initOracleClient({
    libDir: process.env.ORACLE_CLIENT_LIB_DIR,
    configDir: process.env.ORACLE_NET_CONFIG_DIR,
  })
}

initOracleClient()

const IDENTIFIER_REGEX = /^[A-Za-z][A-Za-z0-9_$#]*$/

const state = {
  poolInitialized: false,
}

const safeIdentifier = (value, label) => {
  const parts = String(value ?? '').trim().split('.')

  if (!parts.length || parts.some((part) => !IDENTIFIER_REGEX.test(part))) {
    throw new Error(`Invalid SQL identifier for ${label}: ${value}`)
  }

  return parts.join('.')
}

const getColumnConfig = () => ({
  table: safeIdentifier(process.env.ORACLE_TABLE ?? 'CROP_ANALYSES', 'ORACLE_TABLE'),
  crop: safeIdentifier(process.env.ORACLE_COL_CROP ?? 'CROP_NAME', 'ORACLE_COL_CROP'),
  status: safeIdentifier(process.env.ORACLE_COL_STATUS ?? 'STATUS', 'ORACLE_COL_STATUS'),
  createdAt: safeIdentifier(process.env.ORACLE_COL_CREATED_AT ?? 'CREATED_AT', 'ORACLE_COL_CREATED_AT'),
  score: safeIdentifier(process.env.ORACLE_COL_SCORE ?? 'HEALTH_SCORE', 'ORACLE_COL_SCORE'),
})

const getConnectConfig = () => {
  const { ORACLE_USER, ORACLE_PASSWORD, ORACLE_CONNECT_STRING } = process.env

  if (!ORACLE_USER || !ORACLE_PASSWORD || !ORACLE_CONNECT_STRING) {
    throw new Error('Missing Oracle configuration. Set ORACLE_USER, ORACLE_PASSWORD, and ORACLE_CONNECT_STRING.')
  }

  return {
    user: ORACLE_USER,
    password: ORACLE_PASSWORD,
    connectString: ORACLE_CONNECT_STRING,
    poolMin: 0,
    poolMax: Number(process.env.ORACLE_POOL_MAX) || 1,
    poolIncrement: 1,
  }
}

export const initPool = async () => {
  if (state.poolInitialized) {
    return
  }

  await oracledb.createPool(getConnectConfig())
  state.poolInitialized = true
}

export const closePool = async () => {
  if (!state.poolInitialized) {
    return
  }

  await oracledb.getPool().close(5)
  state.poolInitialized = false
}

export const withConnection = async (work) => {
  if (!state.poolInitialized) {
    await initPool()
  }

  const connection = await oracledb.getConnection()

  try {
    return await work(connection)
  } finally {
    await connection.close()
  }
}

const toNumber = (value, fallback = 0) => {
  if (value == null) {
    return fallback
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const normalizeStatus = (value) => {
  if (!value) {
    return 'Unknown'
  }

  const normalized = String(value).trim().toLowerCase()

  if (normalized === 'healthy') {
    return 'Healthy'
  }

  if (normalized === 'diseased') {
    return 'Diseased'
  }

  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

export const getDashboardData = async (limit = 5) => {
  const configuredLimit = Math.min(Math.max(Number(limit) || 5, 1), 25)
  const columns = getColumnConfig()

  const defaultSummarySql = `
    SELECT
      COUNT(*) AS TOTAL_ANALYSES,
      SUM(CASE WHEN UPPER(${columns.status}) = 'DISEASED' THEN 1 ELSE 0 END) AS DISEASED_ANALYSES,
      SUM(CASE WHEN UPPER(${columns.status}) = 'HEALTHY' THEN 1 ELSE 0 END) AS HEALTHY_ANALYSES,
      ROUND(AVG(NVL(${columns.score}, 0))) AS AVG_HEALTH_SCORE
    FROM ${columns.table}
  `

  const defaultRecentSql = `
    SELECT *
    FROM (
      SELECT
        ${columns.crop} AS CROP_NAME,
        ${columns.status} AS STATUS,
        ${columns.createdAt} AS CREATED_AT
      FROM ${columns.table}
      ORDER BY ${columns.createdAt} DESC
    )
    WHERE ROWNUM <= :limit
  `

  const summarySql = process.env.ORACLE_SUMMARY_SQL?.trim() || defaultSummarySql
  const recentSql = process.env.ORACLE_RECENT_SQL?.trim() || defaultRecentSql

  return withConnection(async (connection) => {
    const [summaryResult, recentResult] = await Promise.all([
      connection.execute(summarySql),
      connection.execute(recentSql, { limit: configuredLimit }),
    ])

    const summaryRow = summaryResult.rows?.[0] ?? {}

    const recentAnalyses = (recentResult.rows ?? []).map((row) => ({
      crop: row.CROP_NAME ?? 'Unknown Crop',
      status: normalizeStatus(row.STATUS),
      createdAt: row.CREATED_AT instanceof Date ? row.CREATED_AT.toISOString() : row.CREATED_AT,
    }))

    return {
      summary: {
        totalAnalyses: toNumber(summaryRow.TOTAL_ANALYSES),
        diseased: toNumber(summaryRow.DISEASED_ANALYSES),
        healthy: toNumber(summaryRow.HEALTHY_ANALYSES),
        healthScore: toNumber(summaryRow.AVG_HEALTH_SCORE, 0),
      },
      recentAnalyses,
    }
  })
}

export const pingDatabase = async () => {
  return withConnection(async (connection) => {
    const result = await connection.execute('SELECT 1 AS OK FROM DUAL')
    return result.rows?.[0]?.OK === 1
  })
}
