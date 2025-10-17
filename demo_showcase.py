# demo_showcase.py
from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path
import os, json

def print_section(title):
    print("\n" + "="*len(title))
    print(title)
    print("="*len(title))

def preview_text(s: str, n=200):
    s = s.replace("\r", " ").replace("\n", " ")
    return (s[:n] + ("..." if len(s) > n else ""))

def main():
    client = TestClient(app)
    data_dir = Path("data")

    # 1) 健康检查
    print_section("Health")
    r = client.get("/health")
    print("GET /health ->", r.status_code, r.json())

    # 2) OpenAPI
    print_section("OpenAPI: first 10 paths")
    spec = client.get("/openapi.json").json()
    paths = list(spec.get("paths", {}).keys())
    for p in paths[:10]:
        print(" ", p)

    # 3) CSV 展示（文件内容 + 接口）
    csv_path = data_dir / "users.csv"
    print_section("CSV: show file head + API schema/page")
    if csv_path.exists():
        txt = csv_path.read_text(encoding="utf-8", errors="ignore")
        print("CSV file:", csv_path)
        print("CSV head:", preview_text(txt, 200))
    else:
        print("No data/users.csv")

    r = client.get("/api/v1/data/users/schema")
    print("GET /api/v1/data/users/schema ->", r.status_code, (r.json() if r.status_code==200 else ""))

    r = client.get("/api/v1/data/users", params={"limit": 5})
    print("GET /api/v1/data/users ->", r.status_code)
    if r.status_code == 200:
        js = r.json()
        print("total:", js.get("total"), "items:", len(js.get("items", [])))
        for row in js.get("items", [])[:3]:
            print("  -", row)

    # 4) JSON 展示（文件内容 + 上传接口，multipart 优先，失败回退 JSON body）
    print_section("JSON: show file content + /upload/json")
    json_files = list(data_dir.glob("*.json"))
    if json_files:
        jf = json_files[0]
        print("JSON file:", jf)
        try:
            raw = json.loads(jf.read_text(encoding="utf-8"))
            print("JSON preview:", preview_text(json.dumps(raw) if not isinstance(raw, str) else raw, 220))
        except Exception as e:
            print("JSON read error:", e)

        files = {"file": (jf.name, jf.read_bytes(), "application/json")}
        data = {"dataset_name": "json_demo"}
        r = client.post("/api/v1/upload/json", files=files, data=data)
        print("POST /api/v1/upload/json [multipart] ->", r.status_code)
        if r.status_code >= 400:
            r2 = client.post("/api/v1/upload/json", json={"file_path": str(jf.resolve()), "dataset_name": "json_demo"})
            print("POST /api/v1/upload/json [json fallback abs path] ->", r2.status_code)
            if r2.status_code == 200:
                print("Resp:", preview_text(json.dumps(r2.json()), 220))
        else:
            print("Resp:", preview_text(json.dumps(r.json()), 220))
    else:
        print("No data/*.json")

    # 5) DOCX 展示（列文件名 + 本地读取前几段 + 批量上传接口）
    print_section("DOCX: show names + local previews + /docx-batch-upload")
    docx_files = [p for p in data_dir.rglob("*.docx")]
    if docx_files:
        print("DOCX files:", [str(p) for p in docx_files], "")
        # 本地预览前 3 个文档的前几段文本
        try:
            import docx as docxlib
            for i, p in enumerate(docx_files[:3], 1):
                try:
                    d = docxlib.Document(str(p))
                    paras = [para.text for para in d.paragraphs if para.text.strip()]
                    preview = " ".join(paras)
                    preview = (preview[:220] + "...") if len(preview) > 220 else preview
                    print(f"[Preview {i}] {p.name} -> {preview}")
                except Exception as e:
                    print(f"[Preview {i}] {p.name} -> ERROR reading: {e}")
        except Exception as e:
            print("Local docx preview error:", e)

        abs_paths = [str(p.resolve()) for p in docx_files]
        payload = {"file_paths": abs_paths, "dataset_name": "docx_demo"}
        print("POST payload sample:", {"file_paths": abs_paths[:2], "dataset_name": "docx_demo"})
        r = client.post("/api/v1/docx-batch-upload", json=payload)
        print("POST /api/v1/docx-batch-upload ->", r.status_code)
        if r.status_code == 200:
            print("Resp:", (r.text[:260] + "...") if len(r.text) > 260 else r.text)
        else:
            print("Docx upload failed; server said:", (r.text[:260] + "...") if r.text else r.text)
    else:
        print("No data/**/*.docx found; skip DOCX demo.")

    # 6) LLM
    print_section("LLM: /api/v1/llm/text")
    payload = {"messages":[{"role":"user","content":"Say hello"}]}
    r = client.post("/api/v1/llm/text", json=payload)
    print("POST /api/v1/llm/text ->", r.status_code)
    if r.status_code == 200:
        print("Resp:", preview_text(json.dumps(r.json()), 220))
    else:
        print("LLM endpoint likely needs external config; in tests it’s stubbed.")

if __name__ == "__main__":
    main()
