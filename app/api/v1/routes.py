from fastapi import APIRouter, Query, UploadFile, File, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import tempfile
import os
from pathlib import Path
import json
import shutil
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse
from ...services.docx_service import docx_service

from ...deps import resolve_csv_path
from ...models import (
    DatasetInfo, DatasetSchema, Page,
    TableInfoSchema, TableInfoResponse,   # ✅ Pydantic
    PaginatedResponse, BatchUploadRequest, DatasetResponse,
    DocxBatchUploadRequest, DocxDocumentResponse, DocxDocumentCreate,
    TableInfo,                            # ✅ ORM（仅用于 db.query(TableInfo)...）
)

from ...services.csv_service import csv_service
from ...services.llm_service import llm_service, LLMCompletionRequest, LLMMessage
from ...services.docx_service import docx_service
from ...config import settings
from ...database import get_db

import csv
import sys
sys.path.append('/data/share/lyc_zdjx/zdjx/my_api')
import logic, schemas

router = APIRouter(prefix="/api/v1", tags=["v1"])

@router.get("/datasets", response_model=list[DatasetInfo])
def list_datasets():
    return csv_service.list_datasets()

@router.get("/data/{name}/schema", response_model=DatasetSchema)
def get_schema(name: str):
    path = resolve_csv_path(name)
    return csv_service.get_schema(path)

@router.get("/data/{name}", response_model=Page)
def get_data(
    name: str,
    limit: int = Query(50, ge=0, le=settings.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="col:asc,col2:desc"),
    filter: Optional[str] = Query(None, description="mini filter expr"),
):
    path = resolve_csv_path(name)
    return csv_service.query(path, limit=limit, offset=offset, sort=sort, filter_expr=filter)

@router.get("/data/{name}/count", response_model=int)
def count_data(name: str, filter: Optional[str] = Query(None)):
    path = resolve_csv_path(name)
    return csv_service.count(path, filter)

# 新增API端点 - 上传CSV文件
@router.post("/upload/csv", response_model=TableInfoResponse)
async def upload_csv(
    file: UploadFile = File(...),
    table_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 检查文件类型
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只支持CSV文件")
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
    try:
        # 保存上传的文件
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # 处理CSV文件并插入数据库
        file_path = Path(temp_file.name)
        table_name, _ = csv_service.upload_csv_to_db(file_path, table_name)
        
        # 从数据库获取表信息
        table_info = db.query(TableInfo).filter_by(table_name=table_name).first()
        if not table_info:
            raise HTTPException(status_code=404, detail="表创建失败")
        
        return table_info
    finally:
        # 删除临时文件
        os.unlink(temp_file.name)

# 新增API端点 - 上传JSON文件
@router.post("/upload/json", response_model=TableInfoResponse)
async def upload_json(
    file: UploadFile = File(...),
    table_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 检查文件类型
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="只支持JSON文件")
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
    try:
        # 保存上传的文件
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # 处理JSON文件并插入数据库
        file_path = Path(temp_file.name)
        try:
            table_name, _ = csv_service.upload_json_to_db(file_path, table_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # 从数据库获取表信息
        table_info = db.query(TableInfo).filter_by(table_name=table_name).first()
        if not table_info:
            raise HTTPException(status_code=404, detail="表创建失败")
        
        return table_info
    finally:
        # 删除临时文件
        os.unlink(temp_file.name)

# 新增API端点 - 获取数据库表数据
@router.get("/tables/{table_name}", response_model=PaginatedResponse)
def get_table_data(
    table_name: str,
    limit: int = Query(50, ge=0, le=settings.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="col:asc,col2:desc"),
    filter: Optional[str] = Query(None, description="SQL WHERE条件")
):
    return csv_service.get_table_data(table_name, limit, offset, sort, filter)

# 新增API端点 - 获取所有表信息
@router.get("/tables", response_model=List[TableInfoResponse])
def list_tables(db: Session = Depends(get_db)):
    return db.query(TableInfo).all()

@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(db: Session = Depends(get_db)):
    """获取所有数据集信息"""
    return db.query(Dataset).all()

@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """获取指定数据集信息"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset

@router.get("/datasets/{dataset_id}/tables", response_model=List[TableInfoResponse])
def get_dataset_tables(dataset_id: int, db: Session = Depends(get_db)):
    """获取指定数据集的所有表信息"""
    tables = db.query(TableInfo).filter(TableInfo.dataset_id == dataset_id).all()
    return tables

# DOCX文档API端点
@router.post("/docx-batch-upload")
async def docx_batch_upload(payload: DocxBatchUploadRequest, db: Session = Depends(get_db)):
    """
    请求体（沿用你 demo 的）:
      {
        "file_paths": ["/abs/path/a.docx", "/abs/path/b.docx"],
        "dataset_name": "docx_demo"
      }
    返回:
      200 + {"dataset_id":..., "results":[{status ok/error ...}], "summary":{...}}
    """
    # 将旧结构转换成 service 需要的 files_info:
    files_info = [{"file_path": p} for p in payload.file_paths]

    # 调用你的 service（它会内部创建/拿到 Dataset 并写库）
    res = await docx_service.batch_upload_docx_files(
        dataset_name=payload.dataset_name,
        dataset_description=None,
        files_info=files_info,
    )

    # 统一输出结构（演示友好）
    dataset_id = res["dataset"]["id"]
    normalized = []
    for it in res.get("upload_results", []):
        if it.get("status") == "success":
            normalized.append({
                "file_path": it.get("file_path"),
                "status": "ok",
                "document_id": it.get("document_id"),
                "filename": it.get("filename"),
            })
        else:
            normalized.append({
                "file_path": it.get("file_path"),
                "status": "error",
                "error": it.get("message"),
            })

    summary = {
        "total": len(normalized),
        "success": sum(1 for x in normalized if x["status"] == "ok"),
        "failed":  sum(1 for x in normalized if x["status"] == "error"),
    }
    return {"dataset_id": dataset_id, "results": normalized, "summary": summary}

@router.get("/docx-documents", response_model=Dict[str, Any])
async def get_docx_documents(
    dataset_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    filename: Optional[str] = None
):
    """获取DOCX文档列表"""
    filters = {}
    if filename:
        filters["filename"] = filename
    
    return docx_service.get_docx_documents(dataset_id, skip, limit, filters)

@router.get("/docx-documents/{document_id}", response_model=DocxDocumentResponse)
async def get_docx_document(document_id: int):
    """获取单个DOCX文档"""
    return docx_service.get_docx_document(document_id)

@router.post("/batch-upload")
async def batch_upload(
    request: BatchUploadRequest,
    db: Session = Depends(get_db)
):
    """
    批量上传文件并关联到同一个数据集
    
    - **dataset_name**: 数据集名称
    - **dataset_description**: 数据集描述（可选）
    - **files_info**: 文件信息列表，每个元素包含:
        - file_path: 文件路径
        - table_name: 表名（可选）
        - file_type: 文件类型，支持 "csv" 或 "json"（默认为 "csv"）
    """
    try:
        # 处理文件路径
        processed_files_info = []
        for file_info in request.files_info:
            file_path = file_info.get("file_path")
            if not file_path:
                raise HTTPException(status_code=400, detail="文件路径不能为空")
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                # 复制文件内容
                shutil.copy(file_path, tmp_file.name)
                
                # 更新文件信息
                file_info_copy = file_info.copy()
                file_info_copy["file_path"] = tmp_file.name
                processed_files_info.append(file_info_copy)
        
        # 批量上传文件
        result = csv_service.batch_upload_files(
            dataset_name=request.dataset_name,
            files_info=processed_files_info,
            dataset_description=request.dataset_description
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")

# 大模型API端点
class LLMRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stream: Optional[bool] = False

@router.post("/llm/completion")
async def generate_completion(request: LLMRequest = Body(...)):
    """
    调用大模型生成文本
    
    - **model**: 模型名称，默认使用配置中的模型
    - **messages**: 消息列表，格式为 [{"role": "user", "content": "你好"}]
    - **max_tokens**: 最大生成token数
    - **temperature**: 温度参数
    - **top_p**: top-p采样参数
    - **top_k**: top-k采样参数
    - **stream**: 是否使用流式响应（暂不支持）
    """
    try:
        # 准备参数
        model = request.model or settings.LLM_DEFAULT_MODEL
        kwargs = {}
        
        # 添加可选参数
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        if request.top_k is not None:
            kwargs["top_k"] = request.top_k
            
        # 调用LLM服务
        result = await llm_service.generate_completion(
            model=model,
            messages=request.messages,
            **kwargs
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")

@router.post("/llm/text")
async def generate_text(
    prompt: str = Body(..., embed=True),
    model: Optional[str] = Body(None, embed=True),
    max_tokens: Optional[int] = Body(None, embed=True),
    temperature: Optional[float] = Body(None, embed=True),
    top_p: Optional[float] = Body(None, embed=True),
    top_k: Optional[int] = Body(None, embed=True)
):
    """
    使用简化接口调用大模型生成文本
    
    - **prompt**: 输入文本
    - **model**: 模型名称，默认使用配置中的模型
    - **max_tokens**: 最大生成token数
    - **temperature**: 温度参数
    - **top_p**: top-p采样参数
    - **top_k**: top-k采样参数
    """
    try:
        # 准备参数
        model = model or settings.LLM_DEFAULT_MODEL
        kwargs = {}
        
        # 添加可选参数
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        if top_p is not None:
            kwargs["top_p"] = top_p
        if top_k is not None:
            kwargs["top_k"] = top_k
            
        # 构建消息
        messages = [{"role": "user", "content": prompt}]
        
        # 调用LLM服务
        result = await llm_service.generate_completion(
            model=model,
            messages=messages,
            **kwargs
        )
        
        # 提取生成的文本
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return {"text": content, "full_response": result}
        else:
            return {"text": "", "full_response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")

def get_count(name: str, filter: Optional[str] = Query(None)):
    path = resolve_csv_path(name)
    return csv_service.count(path, filter)


OUTPUT_DIR = '/data/share/lyc_zdjx/zdjx/my_api/output'

@router.post("/generate/", response_model=schemas.GenerateResponse)
def generate_data(request: schemas.GenerateRequest):
    """
    生成数据并返回去重后的结果
    """
    
    raw_output_path = os.path.join(OUTPUT_DIR, f'raw.csv')
    dedup_output_path = os.path.join(OUTPUT_DIR, f'dedup.csv')

    try:
        # 1. 生成数据
        logic.generate_great_data(request.num_samples, request.columns, raw_output_path)

        # 2. 去重数据
        logic.deduplicate_data(raw_output_path, dedup_output_path)

        # 3. 将 CSV 转换为列表
        data_list = logic.csv_to_list(dedup_output_path)

        return schemas.GenerateResponse(data=data_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate_and_predict/", response_model=List[Dict[str, Any]])
async def generate_and_predict(request: schemas.GenerateRequest):
    """
    生成数据，进行预测，并返回最终的预测结果
    """
    raw_output_path = os.path.join(OUTPUT_DIR, 'raw.csv')
    dedup_output_path = os.path.join(OUTPUT_DIR, 'dedup.csv')
    predict_result_path = os.path.join(OUTPUT_DIR, 'predict_output_abnormal_model_reason.csv')

    try:
        # 1. 生成数据
        logic.generate_great_data(request.num_samples, request.columns, raw_output_path)

        # 2. 去重数据
        logic.deduplicate_data(raw_output_path, dedup_output_path)

        # 3. 进行预测
        # 调用 GNN 预测
        predict_result_path = os.path.join(OUTPUT_DIR, "predict_result.csv")
        logic.predict_gnn_data(dedup_output_path, predict_result_path)
    
        # 直接使用预测脚本生成的异常原因文件，避免被解释逻辑覆盖导致 model_attribute 为空
        reason_result_path = os.path.join(OUTPUT_DIR, "predict_result_abnormal_model_reason.csv")
        if not os.path.exists(reason_result_path):
            # 若文件不存在，则回退到规则解释生成
            logic.explain_with_rules(dedup_output_path, predict_result_path, reason_result_path)

        # 读取异常原因结果，返回为表头对应的字典列表
        with open(reason_result_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            results = list(reader)

        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))