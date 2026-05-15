import base64
import hashlib
import hmac
import json
import os
import re
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
load_env_file(BASE_DIR / "database" / ".env")

DISEASE_SEEDS = [
    {
        "disease_id": "POTATO_LATE_BLIGHT",
        "name": "Potato Late Blight",
        "crop_name": "Potato",
        "is_healthy": "N",
        "symptoms": "Water-soaked leaf spots that turn brown or black, white fungal growth in humid weather, and fast leaf collapse.",
        "treatment": "Remove infected leaves, avoid overhead watering, improve airflow, and apply a recommended fungicide for late blight.",
        "prevention": "Use certified seed potatoes, rotate crops, keep foliage dry, and monitor fields closely during cool wet weather.",
        "description": "A destructive potato disease commonly caused by Phytophthora infestans.",
    },
    {
        "disease_id": "POTATO_HEALTHY",
        "name": "Potato healthy",
        "crop_name": "Potato",
        "is_healthy": "Y",
        "symptoms": "No visible disease symptoms; leaves appear green and evenly developed.",
        "treatment": "No treatment needed. Continue regular monitoring and balanced irrigation.",
        "prevention": "Maintain good field sanitation, crop rotation, and regular scouting.",
        "description": "Healthy potato leaf class from the trained model.",
    },
    {
        "disease_id": "POTATO_EARLY_BLIGHT",
        "name": "Potato_Early_blight",
        "crop_name": "Potato",
        "is_healthy": "N",
        "symptoms": "Dark brown leaf spots with concentric rings, usually starting on older lower leaves.",
        "treatment": "Remove infected foliage where practical and use an appropriate fungicide if disease pressure is high.",
        "prevention": "Rotate crops, avoid plant stress, mulch to reduce soil splash, and remove plant debris after harvest.",
        "description": "A fungal potato leaf disease often associated with Alternaria species.",
    },
    {
        "disease_id": "TOMATO_BACTERIAL_SPOT",
        "name": "Tomato Bacterial spot",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Small dark water-soaked leaf spots, yellow halos, and rough scabby spots on fruit.",
        "treatment": "Remove badly affected leaves and use copper-based bactericides where locally recommended.",
        "prevention": "Use disease-free seed, avoid overhead watering, disinfect tools, and rotate away from tomato and pepper.",
        "description": "A bacterial disease that spreads quickly in warm wet conditions.",
    },
    {
        "disease_id": "TOMATO_EARLY_BLIGHT",
        "name": "Tomato Early Blight",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Brown target-like rings on older leaves, yellowing around lesions, and lower leaf drop.",
        "treatment": "Prune infected lower leaves, improve airflow, and apply a suitable fungicide when needed.",
        "prevention": "Stake plants, mulch soil, rotate crops, and remove infected debris.",
        "description": "A common tomato fungal disease caused mainly by Alternaria solani.",
    },
    {
        "disease_id": "TOMATO_HEALTHY",
        "name": "Tomato Healthy",
        "crop_name": "Tomato",
        "is_healthy": "Y",
        "symptoms": "No visible disease symptoms; leaves are green, firm, and normally shaped.",
        "treatment": "No treatment needed. Keep monitoring plant health.",
        "prevention": "Use balanced watering, clean tools, good spacing, and regular scouting.",
        "description": "Healthy tomato leaf class from the trained model.",
    },
    {
        "disease_id": "TOMATO_LATE_BLIGHT",
        "name": "Tomato Late Blight",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Large irregular dark lesions, pale green water-soaked areas, and rapid leaf or stem collapse.",
        "treatment": "Remove infected material, avoid wet foliage, and apply a late-blight fungicide as advised locally.",
        "prevention": "Use resistant varieties where possible, increase plant spacing, and avoid overhead irrigation.",
        "description": "A serious tomato disease commonly caused by Phytophthora infestans.",
    },
    {
        "disease_id": "TOMATO_LEAF_MOLD",
        "name": "Tomato Leaf Mold",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Yellow patches on upper leaf surfaces with olive-gray mold growth underneath.",
        "treatment": "Improve ventilation, remove infected leaves, and use a labeled fungicide if necessary.",
        "prevention": "Reduce humidity, space plants well, and avoid prolonged leaf wetness.",
        "description": "A tomato leaf disease favored by high humidity and poor airflow.",
    },
    {
        "disease_id": "TOMATO_MOSAIC_VIRUS",
        "name": "Tomato mosaic virus",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Mottled light and dark green leaf pattern, distorted leaves, and reduced plant growth.",
        "treatment": "No cure for infected plants. Remove infected plants and control spread through sanitation.",
        "prevention": "Use resistant varieties, wash hands and tools, and avoid handling plants when wet.",
        "description": "A viral tomato disease that spreads through contact and contaminated tools.",
    },
    {
        "disease_id": "TOMATO_TARGET_SPOT",
        "name": "Tomato_Target_Spot",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Small brown lesions that enlarge into target-like spots, often with yellowing tissue around them.",
        "treatment": "Remove infected leaves, increase airflow, and use appropriate fungicides when disease is spreading.",
        "prevention": "Avoid overhead watering, rotate crops, and remove crop residue.",
        "description": "A fungal tomato disease that can reduce foliage and fruit quality.",
    },
    {
        "disease_id": "TOMATO_YELLOW_LEAF_CURL_VIRUS",
        "name": "Tomato_YellowLeaf__Curl_Viru",
        "crop_name": "Tomato",
        "is_healthy": "N",
        "symptoms": "Yellowing, upward leaf curling, stunted growth, and poor fruit set.",
        "treatment": "There is no cure. Remove infected plants and manage whitefly populations.",
        "prevention": "Use resistant varieties, control whiteflies, remove weeds, and protect seedlings with netting.",
        "description": "A viral tomato disease commonly spread by whiteflies.",
    },
]


def label_key(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


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
                  IS_HEALTHY CHAR(1) DEFAULT 'N' NOT NULL,
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
            run_ddl(cursor, "ALTER TABLE AGRIVISION_DISEASES ADD IS_HEALTHY CHAR(1) DEFAULT 'N' NOT NULL", exists_error_code=1430)
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

            for disease in DISEASE_SEEDS:
                cursor.execute(
                    """
                    SELECT ID
                    FROM AGRIVISION_DISEASES
                    WHERE DISEASE_ID = :disease_id OR LOWER(NAME) = LOWER(:name)
                    """,
                    {"disease_id": disease["disease_id"], "name": disease["name"]},
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE AGRIVISION_DISEASES
                        SET DISEASE_ID = :disease_id,
                            NAME = :name,
                            CROP_NAME = :crop_name,
                            IS_HEALTHY = :is_healthy,
                            SYMPTOMS = :symptoms,
                            TREATMENT = :treatment,
                            PREVENTION = :prevention,
                            DESCRIPTION = :description
                        WHERE ID = :id
                        """,
                        {**disease, "id": existing[0]},
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO AGRIVISION_DISEASES
                          (DISEASE_ID, NAME, CROP_NAME, IS_HEALTHY, SYMPTOMS, TREATMENT, PREVENTION, DESCRIPTION)
                        VALUES
                          (:disease_id, :name, :crop_name, :is_healthy, :symptoms, :treatment, :prevention, :description)
                        """,
                        disease,
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
