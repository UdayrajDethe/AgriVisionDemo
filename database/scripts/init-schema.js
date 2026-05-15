import 'dotenv/config'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import oracledb from 'oracledb'

const clientLibDir = process.env.ORACLE_CLIENT_LIB_DIR

if (clientLibDir && oracledb.thin) {
  oracledb.initOracleClient({
    libDir: clientLibDir,
    configDir: process.env.ORACLE_NET_CONFIG_DIR,
  })
}

const requiredConfig = ['ORACLE_USER', 'ORACLE_PASSWORD', 'ORACLE_CONNECT_STRING']
const missingConfig = requiredConfig.filter((key) => !process.env[key])

if (missingConfig.length) {
  throw new Error(`Missing Oracle configuration: ${missingConfig.join(', ')}`)
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const setupSqlPath = path.resolve(scriptDir, '../sql/setup.sql')

const isSlashTerminated = (sql) => {
  const normalized = sql.trimStart().toUpperCase()
  return normalized.startsWith('BEGIN') || normalized.startsWith('CREATE OR REPLACE TRIGGER')
}

const parseSqlScript = (script) => {
  const statements = []
  let current = []

  const pushCurrent = () => {
    const rawStatement = current.join('\n').trim()
    const statement = isSlashTerminated(rawStatement) ? rawStatement : rawStatement.replace(/;$/, '').trim()
    if (statement) {
      statements.push(statement)
    }
    current = []
  }

  for (const rawLine of script.split(/\r?\n/)) {
    const line = rawLine.trim()

    if (line === '/') {
      pushCurrent()
      continue
    }

    if (!line || line.startsWith('--')) {
      continue
    }

    current.push(rawLine)

    const statement = current.join('\n')
    if (!isSlashTerminated(statement) && line.endsWith(';')) {
      pushCurrent()
    }
  }

  pushCurrent()
  return statements
}

const connection = await oracledb.getConnection({
  user: process.env.ORACLE_USER,
  password: process.env.ORACLE_PASSWORD,
  connectString: process.env.ORACLE_CONNECT_STRING,
})

try {
  const setupSql = await fs.readFile(setupSqlPath, 'utf8')
  const statements = parseSqlScript(setupSql)

  for (const statement of statements) {
    await connection.execute(statement)
  }

  await connection.commit()
  console.log(`Oracle schema initialized from ${setupSqlPath}`)
} finally {
  await Promise.race([
    connection.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ])
}

process.exit(0)
