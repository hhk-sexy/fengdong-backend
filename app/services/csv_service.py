from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import pandas as pd
import json
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..config import settings
from ..utils.filtering import apply_filters
from ..database import engine, get_db
from ..models import TableInfo, Dataset, create_dynamic_table

@dataclass
class CachedFrame:
    df: pd.DataFrame
    mtime: float

class CSVService:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._cache: Dict[Path, CachedFrame] = {}

    def _read_csv_cached(self, path: Path) -> pd.DataFrame:
        path = path.resolve()
        mtime = path.stat().st_mtime
        cached = self._cache.get(path)
        if not cached or cached.mtime != mtime:
            df = pd.read_csv(path)
            self._cache[path] = CachedFrame(df=df, mtime=mtime)
        return self._cache[path].df

    def list_datasets(self) -> List[Dict]:
        out = []
        for p in sorted(self.data_dir.glob("*.csv")):
            try:
                df = self._read_csv_cached(p)
                rows = len(df)
            except Exception:
                rows = None
            out.append({"name": p.stem, "path": str(p.resolve()), "rows": rows})
        return out

    def get_schema(self, path: Path) -> Dict:
        df = self._read_csv_cached(path)
        fields = [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns]
        return {"name": path.stem, "fields": fields}

    def query(self, path: Path, limit: int = 50, offset: int = 0,
              sort: Optional[str] = None, filter_expr: Optional[str] = None) -> Dict:
        df = self._read_csv_cached(path)
        if filter_expr:
            df = apply_filters(df, filter_expr)
        total = len(df)

        if sort:
            cols = []
            ascending = []
            for part in sort.split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    col, direction = part.split(":", 1)
                else:
                    col, direction = part, "asc"
                if col not in df.columns:
                    continue
                cols.append(col)
                ascending.append(direction.lower() != "desc")
            if cols:
                df = df.sort_values(by=cols, ascending=ascending, kind="mergesort")

        limit = max(0, min(limit, settings.MAX_PAGE_SIZE))
        offset = max(0, offset)
        page_df = df.iloc[offset: offset + limit]
        items = page_df.to_dict(orient="records")
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    def count(self, path: Path, filter_expr: Optional[str]) -> int:
        df = self._read_csv_cached(path)
        if filter_expr:
            df = apply_filters(df, filter_expr)
        return int(len(df))

    def upload_csv_to_db(self, file_path: Path, table_name: Optional[str] = None, dataset_id: Optional[int] = None) -> Tuple[str, Dict]:
        """
        上传CSV文件并将数据插入到数据库
        
        Args:
            file_path: CSV文件路径
            table_name: 表名，如果不提供则自动生成
            dataset_id: 数据集ID，用于关联表和数据集
            
        Returns:
            表名和表结构信息
        """
        # 读取CSV文件
        df = pd.read_csv(file_path)
        
        # 如果没有提供表名，则使用文件名加UUID
        if not table_name:
            table_name = f"{file_path.stem}_{uuid.uuid4().hex[:8]}"
        
        # 确定列类型
        columns = {}
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                columns[col] = 'int'
            elif pd.api.types.is_float_dtype(df[col]):
                columns[col] = 'float'
            else:
                columns[col] = 'str'
        
        # 创建表
        create_dynamic_table(table_name, columns)
        
        # 将数据插入到表中
        df.to_sql(table_name, engine, if_exists='append', index=False)
        
        # 保存表信息
        with Session(engine) as session:
            table_info = TableInfo(
                table_name=table_name,
                original_filename=file_path.name,
                columns_info=json.dumps(columns),
                dataset_id=dataset_id
            )
            session.add(table_info)
            session.commit()
            
        return table_name, columns
        
    def upload_json_to_db(self, file_path: Path, table_name: Optional[str] = None, dataset_id: Optional[int] = None) -> Tuple[str, Dict]:
        """
        上传JSON文件并将数据插入到数据库
        
        Args:
            file_path: JSON文件路径
            table_name: 表名，如果不提供则自动生成
            dataset_id: 数据集ID，用于关联表和数据集
            
        Returns:
            表名和表结构信息
        """
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 确保JSON数据是列表格式
        if not isinstance(json_data, list):
            if isinstance(json_data, dict):
                # 如果是单个对象，转换为列表
                json_data = [json_data]
            else:
                raise ValueError("JSON数据必须是对象列表或单个对象")
        
        # 如果列表为空，无法处理
        if not json_data:
            raise ValueError("JSON数据不能为空")
        
        # 转换为DataFrame
        df = pd.DataFrame(json_data)
        
        # 如果没有提供表名，则使用文件名加UUID
        if not table_name:
            table_name = f"{file_path.stem}_{uuid.uuid4().hex[:8]}"
        
        # 确定列类型
        columns = {}
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                columns[col] = 'int'
            elif pd.api.types.is_float_dtype(df[col]):
                columns[col] = 'float'
            else:
                columns[col] = 'str'
        
        # 创建表
        create_dynamic_table(table_name, columns)
        
        # 将数据插入到表中
        df.to_sql(table_name, engine, if_exists='append', index=False)
        
        # 保存表信息
        with Session(engine) as session:
            table_info = TableInfo(
                table_name=table_name,
                original_filename=file_path.name,
                columns_info=json.dumps(columns),
                dataset_id=dataset_id
            )
            session.add(table_info)
            session.commit()
            
        return table_name, columns
        
    def batch_upload_files(self, dataset_name: str, files_info: List[Dict[str, Any]], dataset_description: Optional[str] = None) -> Dict[str, Any]:
        """
        批量上传文件并关联到同一个数据集
        
        Args:
            dataset_name: 数据集名称
            files_info: 文件信息列表，每个元素包含 file_path, table_name, file_type
            dataset_description: 数据集描述
            
        Returns:
            包含数据集信息和上传结果的字典
        """
        # 创建数据集
        with Session(engine) as session:
            # 检查数据集是否已存在
            existing_dataset = session.query(Dataset).filter(Dataset.name == dataset_name).first()
            if existing_dataset:
                dataset = existing_dataset
            else:
                dataset = Dataset(
                    name=dataset_name,
                    description=dataset_description
                )
                session.add(dataset)
                session.commit()
                session.refresh(dataset)
            
            dataset_id = dataset.id
        
        # 批量上传文件
        results = []
        for file_info in files_info:
            file_path = Path(file_info["file_path"])
            table_name = file_info.get("table_name")
            file_type = file_info.get("file_type", "csv").lower()
            
            try:
                if file_type == "csv":
                    table_name, column_types = self.upload_csv_to_db(file_path, table_name, dataset_id)
                elif file_type == "json":
                    table_name, column_types = self.upload_json_to_db(file_path, table_name, dataset_id)
                else:
                    raise ValueError(f"不支持的文件类型: {file_type}")
                
                results.append({
                    "file_path": str(file_path),
                    "table_name": table_name,
                    "status": "success",
                    "columns": column_types
                })
            except Exception as e:
                results.append({
                    "file_path": str(file_path),
                    "status": "error",
                    "error": str(e)
                })
        
        # 返回结果
        return {
            "dataset": {
                "id": dataset_id,
                "name": dataset_name,
                "description": dataset_description
            },
            "upload_results": results
        }
    
    def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0,
                      sort: Optional[str] = None, filter_expr: Optional[str] = None) -> Dict:
        """
        从数据库获取表数据
        
        Args:
            table_name: 表名
            limit: 每页记录数
            offset: 偏移量
            sort: 排序表达式
            filter_expr: 过滤表达式
            
        Returns:
            分页数据
        """
        # 构建查询
        query = f"SELECT * FROM {table_name}"
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        
        # 添加过滤条件
        if filter_expr:
            # 简单实现，实际应用中需要更安全的处理
            query += f" WHERE {filter_expr}"
            count_query += f" WHERE {filter_expr}"
        
        # 添加排序
        if sort:
            sort_parts = []
            for part in sort.split(","):
                part = part.strip()
                if not part:
                    continue
                if ":" in part:
                    col, direction = part.split(":", 1)
                    direction = "DESC" if direction.lower() == "desc" else "ASC"
                else:
                    col, direction = part, "ASC"
                sort_parts.append(f"{col} {direction}")
            
            if sort_parts:
                query += f" ORDER BY {', '.join(sort_parts)}"
        
        # 添加分页
        limit = max(0, min(limit, settings.MAX_PAGE_SIZE))
        offset = max(0, offset)
        query += f" LIMIT {limit} OFFSET {offset}"
        
        # 执行查询
        with engine.connect() as conn:
            # 获取总记录数
            total_result = conn.execute(text(count_query))
            total = total_result.scalar()
            
            # 获取分页数据
            result = conn.execute(text(query))
            items = [dict(row._mapping) for row in result]
        
        return {"total": total, "limit": limit, "offset": offset, "items": items}

csv_service = CSVService(Path(settings.DATA_DIR))