# Oracle API (AgriVision)

This API serves dashboard data and authentication from Oracle.

## 1) Install dependencies

```bash
cd database
npm install
```

## 2) Configure environment

Copy `.env.example` to `.env` and set:

- `ORACLE_USER`
- `ORACLE_PASSWORD`
- `ORACLE_CONNECT_STRING`

If your table/column names differ, update the `ORACLE_TABLE` and `ORACLE_COL_*` values.

## 3) Start API

```bash
npm run dev
```

Server runs at `http://localhost:4000`.

## 4) Start frontend

```bash
cd ../frontend
npm run dev
```

Frontend calls `/api/dashboard` through Vite proxy.

## Endpoints

- `GET /api/health` -> Oracle connectivity check
- `GET /api/dashboard?limit=5` -> summary and recent analyses
- `POST /api/auth/register` -> create a user in Oracle
- `POST /api/auth/login` -> login and receive a token

## Tables

- `AGRIVISION_USERS` -> login/register users
- `AGRIVISION_DISEASES` -> potato/tomato model classes and treatment guidance
- `AGRIVISION_ANALYSES` -> uploaded image prediction history
- `CROP_ANALYSES` -> crop dashboard summary data

`npm run db:init` creates the full schema and seeds these model classes:

- Potato Late Blight
- Potato healthy
- Potato_Early_blight
- Tomato Bacterial spot
- Tomato Early Blight
- Tomato Healthy
- Tomato Late Blight
- Tomato Leaf Mold
- Tomato mosaic virus
- Tomato_Target_Spot
- Tomato_YellowLeaf__Curl_Viru
