import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def load_env_file(path):
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(BASE_DIR / ".env")
load_env_file(BASE_DIR.parent / "database" / ".env")


def _get_oracledb():
    try:
        import oracledb
    except ImportError as exc:
        raise RuntimeError("Missing Python package 'oracledb'. Run: pip install -r requirements.txt") from exc

    lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    config_dir = os.getenv("ORACLE_NET_CONFIG_DIR")

    if lib_dir and getattr(oracledb, "is_thin_mode", lambda: True)():
        oracledb.init_oracle_client(lib_dir=lib_dir, config_dir=config_dir)

    oracledb.defaults.fetch_lobs = False
    oracledb.defaults.fetch_decimals = False
    return oracledb


def get_connection():
    oracledb = _get_oracledb()
    required = ["ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_CONNECT_STRING"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise RuntimeError(f"Missing Oracle configuration: {', '.join(missing)}")

    return oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_CONNECT_STRING"),
    )


def dict_rows(cursor):
    columns = [column[0] for column in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def execute_query(sql, params=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or {})
            return dict_rows(cursor)


def execute_one(sql, params=None):
    rows = execute_query(sql, params)
    return rows[0] if rows else None


def run_ddl(cursor, sql, exists_error_code=955):
    try:
        cursor.execute(sql)
    except Exception as exc:
        if getattr(exc, "args", None) and getattr(exc.args[0], "code", None) == exists_error_code:
            return
        if getattr(exc, "code", None) == exists_error_code:
            return
        raise


def ensure_schema():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            run_ddl(
                cursor,
                """
                CREATE TABLE CROP_ANALYSES (
                  ID NUMBER PRIMARY KEY,
                  CROP_NAME VARCHAR2(100) NOT NULL,
                  STATUS VARCHAR2(20) NOT NULL,
                  CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
                  HEALTH_SCORE NUMBER(3)
                )
                """,
            )
            run_ddl(cursor, "CREATE SEQUENCE CROP_ANALYSES_SEQ START WITH 1 INCREMENT BY 1")
            cursor.execute(
                """
                CREATE OR REPLACE TRIGGER CROP_ANALYSES_BI
                BEFORE INSERT ON CROP_ANALYSES
                FOR EACH ROW
                BEGIN
                  IF :NEW.ID IS NULL THEN
                    SELECT CROP_ANALYSES_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
                  END IF;
                END;
                """
            )

            run_ddl(
                cursor,
                """
                CREATE TABLE AGRIVISION_USERS (
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
                """,
            )
            run_ddl(cursor, "CREATE SEQUENCE AGRIVISION_USERS_SEQ START WITH 1 INCREMENT BY 1")
            cursor.execute(
                """
                CREATE OR REPLACE TRIGGER AGRIVISION_USERS_BI
                BEFORE INSERT ON AGRIVISION_USERS
                FOR EACH ROW
                BEGIN
                  IF :NEW.ID IS NULL THEN
                    SELECT AGRIVISION_USERS_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
                  END IF;
                END;
                """
            )

            run_ddl(
                cursor,
                """
                CREATE TABLE AGRIVISION_DISEASES (
                  ID NUMBER PRIMARY KEY,
                  DISEASE_ID VARCHAR2(40) NOT NULL,
                  NAME VARCHAR2(120) NOT NULL,
                  CROP_NAME VARCHAR2(100),
                  SYMPTOMS CLOB,
                  TREATMENT CLOB,
                  PREVENTION CLOB,
                  DESCRIPTION CLOB,
                  CREATED_AT DATE DEFAULT SYSDATE NOT NULL,
                  CONSTRAINT AGRIVISION_DISEASES_NAME_UQ UNIQUE (NAME)
                )
                """,
            )
            run_ddl(cursor, "CREATE SEQUENCE AGRIVISION_DISEASES_SEQ START WITH 1 INCREMENT BY 1")
            cursor.execute(
                """
                CREATE OR REPLACE TRIGGER AGRIVISION_DISEASES_BI
                BEFORE INSERT ON AGRIVISION_DISEASES
                FOR EACH ROW
                BEGIN
                  IF :NEW.ID IS NULL THEN
                    SELECT AGRIVISION_DISEASES_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
                  END IF;
                END;
                """
            )

            run_ddl(
                cursor,
                """
                CREATE TABLE AGRIVISION_ANALYSES (
                  ID NUMBER PRIMARY KEY,
                  ANALYSIS_ID VARCHAR2(40) NOT NULL,
                  USER_ID VARCHAR2(40),
                  DISEASE_ID VARCHAR2(40),
                  IMAGE_NAME VARCHAR2(255),
                  PREDICTED_LABEL VARCHAR2(150),
                  CONFIDENCE NUMBER(8, 4),
                  ROBOFLOW_RESPONSE CLOB,
                  CREATED_AT DATE DEFAULT SYSDATE NOT NULL
                )
                """,
            )
            run_ddl(cursor, "CREATE SEQUENCE AGRIVISION_ANALYSES_SEQ START WITH 1 INCREMENT BY 1")
            cursor.execute(
                """
                CREATE OR REPLACE TRIGGER AGRIVISION_ANALYSES_BI
                BEFORE INSERT ON AGRIVISION_ANALYSES
                FOR EACH ROW
                BEGIN
                  IF :NEW.ID IS NULL THEN
                    SELECT AGRIVISION_ANALYSES_SEQ.NEXTVAL INTO :NEW.ID FROM DUAL;
                  END IF;
                END;
                """
            )

            connection.commit()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1).hex()
    return f"{salt}:{digest}"


def verify_password(password, stored_hash):
    try:
        salt, digest = stored_hash.split(":", 1)
    except ValueError:
        return False

    candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(candidate, digest)


def base64url(value):
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def sign_token(payload):
    secret = os.getenv("JWT_SECRET", "agrivision_secret").encode("utf-8")
    body = {**payload, "exp": int(time.time()) + 24 * 60 * 60}
    header_part = base64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    body_part = base64url(json.dumps(body).encode("utf-8"))
    unsigned = f"{header_part}.{body_part}"
    signature = hmac.new(secret, unsigned.encode("utf-8"), hashlib.sha256).digest()
    return f"{unsigned}.{base64url(signature)}"


def parse_token(auth_header):
    if not auth_header:
        return None

    token = auth_header.replace("Bearer ", "", 1)
    parts = token.split(".")
    if len(parts) != 3:
        return None

    secret = os.getenv("JWT_SECRET", "agrivision_secret").encode("utf-8")
    expected = base64url(hmac.new(secret, f"{parts[0]}.{parts[1]}".encode("utf-8"), hashlib.sha256).digest())

    if not hmac.compare_digest(expected, parts[2]):
        return None

    padded_body = parts[1] + "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded_body.encode("utf-8")))

    if payload.get("exp", 0) < int(time.time()):
        return None

    return payload


def iso_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)
