import 'dotenv/config'
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

const tableName = process.env.ORACLE_TABLE || 'CROP_ANALYSES'

const createTableSql = `
  CREATE TABLE ${tableName} (
    ID NUMBER PRIMARY KEY,
    CROP_NAME VARCHAR2(100) NOT NULL,
    STATUS VARCHAR2(20) NOT NULL,
    CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
    HEALTH_SCORE NUMBER(3)
  )
`

const createSequenceSql = `CREATE SEQUENCE ${tableName}_SEQ START WITH 1 INCREMENT BY 1`

const createTriggerSql = `
  CREATE OR REPLACE TRIGGER ${tableName}_BI
  BEFORE INSERT ON ${tableName}
  FOR EACH ROW
  BEGIN
    IF :NEW.ID IS NULL THEN
      SELECT ${tableName}_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
    END IF;
  END;
`

const sampleRows = [
  ['Tomato', 'Healthy', 1, 92],
  ['Potato', 'Diseased', 2, 48],
  ['Wheat', 'Healthy', 3, 86],
  ['Rice', 'Diseased', 4, 55],
  ['Maize', 'Healthy', 5, 78],
]

const connection = await oracledb.getConnection({
  user: process.env.ORACLE_USER,
  password: process.env.ORACLE_PASSWORD,
  connectString: process.env.ORACLE_CONNECT_STRING,
})

try {
  try {
    await connection.execute(createTableSql)
    console.log(`Created table ${tableName}`)
  } catch (error) {
    if (error.errorNum === 955) {
      console.log(`Table ${tableName} already exists`)
    } else {
      throw error
    }
  }

  try {
    await connection.execute(createSequenceSql)
    console.log(`Created sequence ${tableName}_SEQ`)
  } catch (error) {
    if (error.errorNum === 955) {
      console.log(`Sequence ${tableName}_SEQ already exists`)
    } else {
      throw error
    }
  }

  await connection.execute(createTriggerSql)
  console.log(`Created or replaced trigger ${tableName}_BI`)

  const countResult = await connection.execute(`SELECT COUNT(*) AS TOTAL FROM ${tableName}`, [], {
    outFormat: oracledb.OUT_FORMAT_OBJECT,
  })
  const total = Number(countResult.rows?.[0]?.TOTAL || 0)

  if (total === 0) {
    await connection.executeMany(
      `INSERT INTO ${tableName} (CROP_NAME, STATUS, CREATED_AT, HEALTH_SCORE)
       VALUES (:cropName, :status, SYSDATE - :daysAgo, :healthScore)`,
      sampleRows,
      {
        bindDefs: [
          { type: oracledb.STRING, maxSize: 100 },
          { type: oracledb.STRING, maxSize: 20 },
          { type: oracledb.NUMBER },
          { type: oracledb.NUMBER },
        ],
      },
    )
    await connection.commit()
    console.log(`Inserted ${sampleRows.length} sample rows`)
  } else {
    console.log(`Skipped sample rows because ${tableName} already has ${total} row(s)`)
  }
} finally {
  await Promise.race([
    connection.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ])
}

process.exit(0)
