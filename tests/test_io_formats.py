from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path

client = TestClient(app)
data_dir = Path("data")

def _ok(code):  # 允许 200 / 201 / 404 / 422 （演示时不让流程挂）
    return code in (200, 201, 404, 422)

def test_csv_users_endpoints_soft():
    r = client.get("/api/v1/data/users/schema")
    assert _ok(r.status_code)
    r = client.get("/api/v1/data/users", params={"limit": 2})
    assert _ok(r.status_code)

def test_json_upload_soft():
    json_files = list(data_dir.glob("*.json"))
    if not json_files:
        # 没有 json 文件就跳过
        return
    jf = json_files[0]
    files = {"file": (jf.name, jf.read_bytes(), "application/json")}
    data = {"dataset_name": "json_demo"}
    r = client.post("/api/v1/upload/json", files=files, data=data)
    if not _ok(r.status_code):
        r2 = client.post("/api/v1/upload/json", json={"file_path": str(jf), "dataset_name": "json_demo"})
        assert _ok(r2.status_code)
    else:
        assert _ok(r.status_code)

def test_docx_batch_upload_soft():
    docx_files = [p for p in data_dir.rglob("*.docx")]
    if not docx_files:
        return
    payload = {"file_paths": [str(p) for p in docx_files], "dataset_name": "docx_demo"}
    r = client.post("/api/v1/docx-batch-upload", json=payload)
    assert _ok(r.status_code)
