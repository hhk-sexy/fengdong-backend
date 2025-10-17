# app/models.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

# ---------- SQLAlchemy ORM ----------
from sqlalchemy import (
    Column, Integer, String, Float, Text, Table, MetaData
)
from .database import Base, engine  # Base 来自 app/database.py 的 declarative_base()

# 单独的 metadata 用于“动态数据表”（CSV/JSON 导入产生的表），避免和 ORM 冲突
dynamic_metadata = MetaData()
from sqlalchemy import Column, Integer, String, Text, DateTime, func

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class TableInfo(Base):
    __tablename__ = "table_info"
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String, unique=True, nullable=False)
    original_filename = Column(String, nullable=True)
    columns_info = Column(Text, nullable=False)  # 存列信息的 JSON 字符串
    dataset_id = Column(Integer, nullable=True)

class DocxDocument(Base):
    __tablename__ = "docx_documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, nullable=True)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
def create_dynamic_table(table_name: str, columns: Dict[str, str]):
    """
    columns 例: {"id":"int","name":"str","amount":"float"}
    规则：
      - 如果 columns 里已有 "id"，用它（并设为主键），不再额外造自增 id；
      - 如果没有 "id"，自动加一个自增主键 id。
    """
    cols = []
    has_id = "id" in columns

    if not has_id:
        cols.append(Column("id", Integer, primary_key=True, autoincrement=True))

    for col_name, col_type in columns.items():
        if col_name == "id":
            # 用用户的 id 列作为主键
            if col_type == "int":
                cols.append(Column("id", Integer, primary_key=True))
            elif col_type == "float":
                cols.append(Column("id", Float, primary_key=True))
            else:
                cols.append(Column("id", String, primary_key=True))
            continue

        if col_type == "int":
            cols.append(Column(col_name, Integer))
        elif col_type == "float":
            cols.append(Column(col_name, Float))
        else:
            cols.append(Column(col_name, String))

    table = Table(table_name, dynamic_metadata, *cols)
    dynamic_metadata.create_all(engine)
    return table

# ---------- Pydantic Schemas ----------
from pydantic import BaseModel, Field, ConfigDict

class DatasetInfo(BaseModel):
    name: str
    rows: int | None = None
    cols: int | None = None

class ColumnInfo(BaseModel):
    name: str
    dtype: str

class DatasetSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    # 后端实际返回键是 "fields"，这里用 alias 兼容；对外模型字段名仍为 columns
    columns: List[ColumnInfo] = Field(alias="fields")

class Page(BaseModel):
    total: int
    items: List[Dict[str, Any]]

# 注意：避免与 ORM TableInfo 重名
class TableInfoSchema(BaseModel):
    table_name: str
    columns: List[str] = []

class TableInfoResponse(BaseModel):
    table_name: str
    columns: List[Dict[str, Any]] = []

class PaginatedResponse(BaseModel):
    total: int
    items: List[Any]

class BatchUploadRequest(BaseModel):
    dataset_name: Optional[str] = None

class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class DocxBatchUploadRequest(BaseModel):
    file_paths: List[str]
    dataset_name: str

# ✅ 你缺的就是这个：用于创建 DOCX 的入参 Schema
class DocxDocumentCreate(BaseModel):
    dataset_id: Optional[int] = None
    filename: str
    content: Optional[str] = None

class DocxDocumentResponse(BaseModel):
    id: int
    dataset_id: int
    filename: str
    content_preview: Optional[str] = None

