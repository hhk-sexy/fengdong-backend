from fastapi import HTTPException
from .config import settings
from pathlib import Path

def resolve_csv_path(name: str) -> Path:
    fname = name if name.endswith('.csv') else f"{name}.csv"
    path = (Path(settings.DATA_DIR) / fname).resolve()
    data_root = Path(settings.DATA_DIR).resolve()
    if data_root not in path.parents and path != data_root:
        raise HTTPException(status_code=400, detail="Invalid dataset path")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{name}' not found")
    return path