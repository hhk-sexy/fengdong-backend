from typing import Dict, Any, Optional, List, Union
import httpx
import json
from pydantic import BaseModel, Field

from ..config import settings

class LLMMessage(BaseModel):
    role: str
    content: str

class LLMCompletionRequest(BaseModel):
    model: str = Field(default=settings.LLM_DEFAULT_MODEL)
    messages: List[LLMMessage]
    max_tokens: Optional[int] = Field(default=settings.LLM_DEFAULT_MAX_TOKENS)
    temperature: Optional[float] = Field(default=settings.LLM_DEFAULT_TEMPERATURE)
    top_p: Optional[float] = Field(default=settings.LLM_DEFAULT_TOP_P)
    top_k: Optional[int] = Field(default=settings.LLM_DEFAULT_TOP_K)
    stream: Optional[bool] = Field(default=False)

class LLMService:
    """
    调用本地部署的大模型服务
    使用vLLM框架的OpenAI兼容API
    """
    
    def __init__(self, base_url: str = settings.LLM_API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT)
    
    async def generate_completion(self, 
                                 model: str = settings.LLM_DEFAULT_MODEL,
                                 messages: List[Dict[str, str]] = None,
                                 prompt: str = None,
                                 max_tokens: int = settings.LLM_DEFAULT_MAX_TOKENS,
                                 temperature: float = settings.LLM_DEFAULT_TEMPERATURE,
                                 top_p: float = settings.LLM_DEFAULT_TOP_P,
                                 top_k: int = settings.LLM_DEFAULT_TOP_K,
                                 **kwargs) -> Dict[str, Any]:
        """
        生成文本补全
        
        Args:
            model: 模型名称
            messages: 消息列表，格式为 [{"role": "user", "content": "你好"}]
            prompt: 如果不使用messages，可以直接提供prompt文本
            max_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top-p采样参数
            top_k: top-k采样参数
            **kwargs: 其他OpenAI兼容参数
            
        Returns:
            API响应结果
        """
        # 构建请求URL
        url = f"{self.base_url}/chat/completions"
        
        # 构建请求数据
        if messages is None and prompt is not None:
            # 如果提供了prompt而不是messages，转换为messages格式
            messages = [{"role": "user", "content": prompt}]
        elif messages is None and prompt is None:
            raise ValueError("必须提供messages或prompt参数")
        
        # 构建请求体
        request_data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }
        
        # 添加其他参数
        for key, value in kwargs.items():
            request_data[key] = value
        
        # 发送请求
        response = await self.client.post(
            url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        # 处理响应
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                if "error" in error_json:
                    error_detail = error_json["error"]
            except:
                pass
            
            raise Exception(f"LLM API调用失败: {response.status_code}, {error_detail}")
        
        return response.json()
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

# 创建服务实例
llm_service = LLMService()