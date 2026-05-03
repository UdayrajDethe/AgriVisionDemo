import crypto from 'node:crypto'
import { withConnection } from './oracle.js'

const USERS_TABLE = 'AGRIVISION_USERS'
const USERS_SEQUENCE = 'AGRIVISION_USERS_SEQ'
const USERS_TRIGGER = 'AGRIVISION_USERS_BI'

const encodeBase64Url = (value) =>
  Buffer.from(value)
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')

const hashPassword = (password) => {
  const salt = crypto.randomBytes(16).toString('hex')
  const hash = crypto.scryptSync(password, salt, 64).toString('hex')
  return `${salt}:${hash}`
}

const verifyPassword = (password, storedHash) => {
  const [salt, hash] = String(storedHash || '').split(':')

  if (!salt || !hash) {
    return false
  }

  const candidate = crypto.scryptSync(password, salt, 64)
  const expected = Buffer.from(hash, 'hex')

  return candidate.length === expected.length && crypto.timingSafeEqual(candidate, expected)
}

const signToken = (payload) => {
  const secret = process.env.JWT_SECRET || 'agrivision_secret'
  const header = { alg: 'HS256', typ: 'JWT' }
  const expiresAt = Math.floor(Date.now() / 1000) + 24 * 60 * 60
  const body = { ...payload, exp: expiresAt }
  const unsignedToken = `${encodeBase64Url(JSON.stringify(header))}.${encodeBase64Url(JSON.stringify(body))}`
  const signature = crypto.createHmac('sha256', secret).update(unsignedToken).digest('base64url')

  return `${unsignedToken}.${signature}`
}

const runDdl = async (connection, sql, existsErrorCode, label) => {
  try {
    await connection.execute(sql)
    console.log(`Created ${label}`)
  } catch (error) {
    if (error.errorNum !== existsErrorCode) {
      throw error
    }
  }
}

export const ensureAuthSchema = async () => {
  await withConnection(async (connection) => {
    await runDdl(
      connection,
      `
        CREATE TABLE ${USERS_TABLE} (
          ID NUMBER PRIMARY KEY,
          USER_ID VARCHAR2(40) NOT NULL,
          NAME VARCHAR2(100) NOT NULL,
          EMAIL VARCHAR2(150) NOT NULL,
          PHONE VARCHAR2(20),
          PASSWORD_HASH VARCHAR2(200) NOT NULL,
          LOCATION VARCHAR2(150),
          CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
          CONSTRAINT AGRIVISION_USERS_EMAIL_UQ UNIQUE (EMAIL)
        )
      `,
      955,
      USERS_TABLE,
    )

    await runDdl(
      connection,
      `CREATE SEQUENCE ${USERS_SEQUENCE} START WITH 1 INCREMENT BY 1`,
      955,
      USERS_SEQUENCE,
    )

    await connection.execute(`
      CREATE OR REPLACE TRIGGER ${USERS_TRIGGER}
      BEFORE INSERT ON ${USERS_TABLE}
      FOR EACH ROW
      BEGIN
        IF :NEW.ID IS NULL THEN
          SELECT ${USERS_SEQUENCE}.NEXTVAL INTO :NEW.ID FROM DUAL;
        END IF;
      END;
    `)
  })
}

export const registerUser = async (req, res) => {
  const { name, email, phone, password, location } = req.body
  const normalizedEmail = String(email || '').trim().toLowerCase()

  if (!name || !normalizedEmail || !password) {
    return res.status(400).json({ message: 'Name, email, and password are required' })
  }

  try {
    await withConnection(async (connection) => {
      const existingUser = await connection.execute(
        `SELECT USER_ID FROM ${USERS_TABLE} WHERE LOWER(EMAIL) = :email`,
        { email: normalizedEmail },
      )

      if (existingUser.rows?.length) {
        return res.status(400).json({ message: 'User already exists' })
      }

      const userId = Date.now().toString()
      const passwordHash = hashPassword(password)

      await connection.execute(
        `
          INSERT INTO ${USERS_TABLE} (USER_ID, NAME, EMAIL, PHONE, PASSWORD_HASH, LOCATION)
          VALUES (:userId, :name, :email, :phone, :passwordHash, :location)
        `,
        {
          userId,
          name: String(name).trim(),
          email: normalizedEmail,
          phone: phone ? String(phone).trim() : null,
          passwordHash,
          location: location ? String(location).trim() : null,
        },
        { autoCommit: true },
      )

      return res.status(201).json({ message: 'Registration successful' })
    })
  } catch (error) {
    console.error('Registration failed:', error)
    return res.status(500).json({ message: 'Registration failed', details: error.message })
  }
}

export const loginUser = async (req, res) => {
  const { email, password } = req.body
  const normalizedEmail = String(email || '').trim().toLowerCase()

  if (!normalizedEmail || !password) {
    return res.status(400).json({ message: 'Email and password are required' })
  }

  try {
    await withConnection(async (connection) => {
      const result = await connection.execute(
        `
          SELECT USER_ID, NAME, EMAIL, PHONE, PASSWORD_HASH, LOCATION
          FROM ${USERS_TABLE}
          WHERE LOWER(EMAIL) = :email
        `,
        { email: normalizedEmail },
      )

      const user = result.rows?.[0]

      if (!user || !verifyPassword(password, user.PASSWORD_HASH)) {
        return res.status(400).json({ message: 'Invalid email or password' })
      }

      const token = signToken({ id: user.USER_ID, email: user.EMAIL })

      return res.status(200).json({
        message: 'Login successful',
        token,
        user: {
          id: user.USER_ID,
          name: user.NAME,
          email: user.EMAIL,
          phone: user.PHONE,
          location: user.LOCATION,
        },
      })
    })
  } catch (error) {
    console.error('Login failed:', error)
    return res.status(500).json({ message: 'Login failed', details: error.message })
  }
}
