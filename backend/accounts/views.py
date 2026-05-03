import json
import os
import time
import urllib.parse
import urllib.request
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .oracle_client import (
    dict_rows,
    ensure_schema,
    execute_one,
    execute_query,
    get_connection,
    hash_password,
    iso_datetime,
    parse_token,
    sign_token,
    verify_password,
)

_SCHEMA_READY = False


def _ensure_schema_ready():
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        ensure_schema()
        _SCHEMA_READY = True


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


def _error(message, status=400, details=None):
    payload = {"message": message}
    if details:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def _user_payload(row):
    return {
        "id": row["USER_ID"],
        "name": row["NAME"],
        "email": row["EMAIL"],
        "phone": row.get("PHONE"),
        "location": row.get("LOCATION"),
    }


def health(_request):
    try:
        row = execute_one("SELECT 1 AS OK FROM DUAL")
        return JsonResponse({"ok": row and row.get("OK") == 1})
    except Exception as exc:
        return JsonResponse(
            {
                "ok": False,
                "message": "Oracle connection failed",
                "details": str(exc),
            },
            status=500,
        )


def dashboard(request):
    try:
        limit = min(max(int(request.GET.get("limit", 5)), 1), 25)
    except ValueError:
        limit = 5

    try:
        _ensure_schema_ready()
        summary = execute_one(
            """
            SELECT
              COUNT(*) AS TOTAL_ANALYSES,
              SUM(CASE WHEN UPPER(STATUS) = 'DISEASED' THEN 1 ELSE 0 END) AS DISEASED_ANALYSES,
              SUM(CASE WHEN UPPER(STATUS) = 'HEALTHY' THEN 1 ELSE 0 END) AS HEALTHY_ANALYSES,
              ROUND(AVG(NVL(HEALTH_SCORE, 0))) AS AVG_HEALTH_SCORE
            FROM CROP_ANALYSES
            """
        ) or {}
        recent = execute_query(
            """
            SELECT *
            FROM (
              SELECT CROP_NAME, STATUS, CREATED_AT
              FROM CROP_ANALYSES
              ORDER BY CREATED_AT DESC
            )
            WHERE ROWNUM <= :limit
            """,
            {"limit": limit},
        )

        return JsonResponse(
            {
                "summary": {
                    "totalAnalyses": int(summary.get("TOTAL_ANALYSES") or 0),
                    "diseased": int(summary.get("DISEASED_ANALYSES") or 0),
                    "healthy": int(summary.get("HEALTHY_ANALYSES") or 0),
                    "healthScore": int(summary.get("AVG_HEALTH_SCORE") or 0),
                },
                "recentAnalyses": [
                    {
                        "crop": row.get("CROP_NAME") or "Unknown Crop",
                        "status": (row.get("STATUS") or "Unknown").title(),
                        "createdAt": iso_datetime(row.get("CREATED_AT")),
                    }
                    for row in recent
                ],
            }
        )
    except Exception as exc:
        return _error("Failed to fetch dashboard data from Oracle", status=500, details=str(exc))


@csrf_exempt
def register_user(request):
    if request.method != "POST":
        return _error("Method not allowed", status=405)

    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON")

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    location = (data.get("location") or "").strip()
    password = data.get("password") or ""

    if not all([name, email, password]):
        return _error("Name, email, and password are required")

    try:
        _ensure_schema_ready()
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT USER_ID FROM AGRIVISION_USERS WHERE LOWER(EMAIL) = :email", {"email": email})
                if cursor.fetchone():
                    return _error("User already exists")

                cursor.execute(
                    """
                    INSERT INTO AGRIVISION_USERS (USER_ID, NAME, EMAIL, PHONE, PASSWORD_HASH, LOCATION)
                    VALUES (:user_id, :name, :email, :phone, :password_hash, :location)
                    """,
                    {
                        "user_id": str(int(time.time() * 1000)),
                        "name": name,
                        "email": email,
                        "phone": phone or None,
                        "password_hash": hash_password(password),
                        "location": location or None,
                    },
                )
                connection.commit()

        return JsonResponse({"message": "Registration successful"}, status=201)
    except Exception as exc:
        return _error("Registration failed", status=500, details=str(exc))


@csrf_exempt
def login_user(request):
    if request.method != "POST":
        return _error("Method not allowed", status=405)

    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON")

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return _error("Email and password are required")

    try:
        _ensure_schema_ready()
        row = execute_one(
            """
            SELECT USER_ID, NAME, EMAIL, PHONE, PASSWORD_HASH, LOCATION
            FROM AGRIVISION_USERS
            WHERE LOWER(EMAIL) = :email
            """,
            {"email": email},
        )

        if not row or not verify_password(password, row["PASSWORD_HASH"]):
            return _error("Invalid email or password")

        return JsonResponse(
            {
                "message": "Login successful",
                "token": sign_token({"id": row["USER_ID"], "email": row["EMAIL"]}),
                "user": _user_payload(row),
            }
        )
    except Exception as exc:
        return _error("Login failed", status=500, details=str(exc))


def diseases(_request):
    try:
        _ensure_schema_ready()
        rows = execute_query(
            """
            SELECT DISEASE_ID, NAME, CROP_NAME, SYMPTOMS, TREATMENT, PREVENTION, DESCRIPTION
            FROM AGRIVISION_DISEASES
            ORDER BY NAME
            """
        )
        return JsonResponse({"diseases": rows})
    except Exception as exc:
        return _error("Failed to fetch diseases", status=500, details=str(exc))


def history(request):
    token = parse_token(request.headers.get("Authorization"))
    if not token:
        return _error("Unauthorized", status=401)

    try:
        _ensure_schema_ready()
        rows = execute_query(
            """
            SELECT ANALYSIS_ID, DISEASE_ID, IMAGE_NAME, PREDICTED_LABEL, CONFIDENCE, CREATED_AT
            FROM AGRIVISION_ANALYSES
            WHERE USER_ID = :user_id
            ORDER BY CREATED_AT DESC
            """,
            {"user_id": token["id"]},
        )
        return JsonResponse(
            {
                "history": [
                    {
                        "analysisId": row["ANALYSIS_ID"],
                        "diseaseId": row.get("DISEASE_ID"),
                        "imageName": row.get("IMAGE_NAME"),
                        "predictedLabel": row.get("PREDICTED_LABEL"),
                        "confidence": row.get("CONFIDENCE"),
                        "createdAt": iso_datetime(row.get("CREATED_AT")),
                    }
                    for row in rows
                ]
            }
        )
    except Exception as exc:
        return _error("Failed to fetch analysis history", status=500, details=str(exc))


def _call_roboflow(image_file):
    api_url = os.getenv("ROBOFLOW_API_URL", "").strip()
    api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()

    if not api_url or not api_key:
        return {
            "predictedLabel": "Unknown",
            "confidence": 0,
            "raw": {"message": "Roboflow is not configured. Set ROBOFLOW_API_URL and ROBOFLOW_API_KEY."},
        }

    boundary = f"----AgriVision{uuid.uuid4().hex}"
    image_bytes = image_file.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{image_file.name}"\r\n'
        f"Content-Type: {image_file.content_type or 'application/octet-stream'}\r\n\r\n"
    ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    query_separator = "&" if "?" in api_url else "?"
    url = f"{api_url}{query_separator}{urllib.parse.urlencode({'api_key': api_key})}"
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    predictions = payload.get("predictions") or []
    top = max(predictions, key=lambda item: item.get("confidence", 0), default={})

    return {
        "predictedLabel": top.get("class") or payload.get("top") or "Unknown",
        "confidence": float(top.get("confidence") or payload.get("confidence") or 0),
        "raw": payload,
    }


@csrf_exempt
def analyze_image(request):
    if request.method != "POST":
        return _error("Method not allowed", status=405)

    token = parse_token(request.headers.get("Authorization"))
    image = request.FILES.get("image")

    if not image:
        return _error("Image file is required")

    try:
        _ensure_schema_ready()
        prediction = _call_roboflow(image)
        disease = execute_one(
            """
            SELECT DISEASE_ID, NAME, CROP_NAME, SYMPTOMS, TREATMENT, PREVENTION, DESCRIPTION
            FROM AGRIVISION_DISEASES
            WHERE LOWER(NAME) = :name
            """,
            {"name": prediction["predictedLabel"].lower()},
        )

        analysis_id = str(int(time.time() * 1000))
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO AGRIVISION_ANALYSES
                      (ANALYSIS_ID, USER_ID, DISEASE_ID, IMAGE_NAME, PREDICTED_LABEL, CONFIDENCE, ROBOFLOW_RESPONSE)
                    VALUES
                      (:analysis_id, :user_id, :disease_id, :image_name, :predicted_label, :confidence, :raw_response)
                    """,
                    {
                        "analysis_id": analysis_id,
                        "user_id": token.get("id") if token else None,
                        "disease_id": disease.get("DISEASE_ID") if disease else None,
                        "image_name": image.name,
                        "predicted_label": prediction["predictedLabel"],
                        "confidence": prediction["confidence"],
                        "raw_response": json.dumps(prediction["raw"]),
                    },
                )
                connection.commit()

        return JsonResponse(
            {
                "analysisId": analysis_id,
                "prediction": {
                    "label": prediction["predictedLabel"],
                    "confidence": prediction["confidence"],
                },
                "disease": disease,
            }
        )
    except Exception as exc:
        return _error("Image analysis failed", status=500, details=str(exc))


def init_schema(_request=None):
    try:
        ensure_schema()
        return JsonResponse({"ok": True, "message": "Oracle schema is ready"})
    except Exception as exc:
        return JsonResponse({"ok": False, "message": "Schema initialization failed", "details": str(exc)}, status=500)
