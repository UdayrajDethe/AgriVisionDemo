# AgriVision Django Backend

Django backend for AgriVision auth, Oracle dashboard data, disease data, Roboflow image analysis, and user analysis history.

## Setup

```powershell
cd backend
py -m pip install -r requirements.txt
py manage.py runserver 4000
```

The React frontend calls `http://localhost:4000`, so Django replaces the old Node/Express backend.

## Endpoints

- `GET /api/health` -> Oracle connectivity check
- `GET /api/dashboard?limit=5` -> dashboard summary and recent analyses
- `POST /api/auth/register` -> register user in Oracle
- `POST /api/auth/login` -> login and receive token
- `GET /api/diseases` -> disease knowledge table
- `GET /api/analysis/history` -> logged-in user's analysis history
- `POST /api/analyze` -> upload image, call Roboflow, store history

## Oracle Tables

- `AGRIVISION_USERS`
- `AGRIVISION_DISEASES`
- `AGRIVISION_ANALYSES`
- `CROP_ANALYSES`

## Environment

Copy `.env.example` to `.env` if needed. If `backend/.env` is missing, Django also reads the existing `database/.env` Oracle settings.

Roboflow is optional until you set:

- `ROBOFLOW_API_URL`
- `ROBOFLOW_API_KEY`