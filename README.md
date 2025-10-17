# FastAPI CSV Backend

A small, extendable service for reading CSVs and exposing them via HTTP.

## Endpoints
- `GET /health`
- `GET /api/v1/datasets`
- `GET /api/v1/data/{name}/schema`
- `GET /api/v1/data/{name}` with `limit`, `offset`, `sort`, `filter`
- `GET /api/v1/data/{name}/count`

## Filter grammar
Use `;` to chain conditions. Supported ops: `== != >= <= > < in ~`.
- Strings can be raw or quoted. `in` expects `[A,B,C]`.
- `~` is case‑insensitive substring.

Examples:
- `status==active;amount>=100`
- `country in [US,JP,CN]`
- `name~alice`

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Example
```bash
curl http://127.0.0.1:8000/api/v1/datasets
curl "http://127.0.0.1:8000/api/v1/data/users?limit=10&sort=age:desc&filter=country==JP;age>=20"
```

## Notes
- CSVs must be in `./data`. Dataset name is filename without `.csv`.
- Large CSVs: consider chunking or using DuckDB/Polars in the future.
- Security: path traversal is blocked; only files in `DATA_DIR` are allowed.



## TODO
- [ ] Add other file type
- [ ] Add Dockerfile
- [ ] Add model function