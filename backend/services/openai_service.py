"""
OpenAI API 服务封装
支持 Chat Completion、Embedding、异步批量调用
"""
from typing import List, Dict, Any, Optional
import asyncio
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from loguru import logger

from backend.config import settings


class OpenAIService:
    """OpenAI API 服务类"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Chat Completion API 调用
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称（默认使用配置中的模型）
            temperature: 温度参数（0-2）
            max_tokens: 最大token数
            json_mode: 是否使用 JSON 模式
        
        Returns:
            str: 模型响应文本
        """
        try:
            kwargs = {
                "model": model or self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            
            # 记录 token 使用量
            usage = response.usage
            logger.debug(
                f"OpenAI API 调用成功 - "
                f"模型: {kwargs['model']}, "
                f"输入: {usage.prompt_tokens} tokens, "
                f"输出: {usage.completion_tokens} tokens, "
                f"总计: {usage.total_tokens} tokens"
            )
            
            return content
        
        except Exception as e:
            logger.error(f"OpenAI Chat Completion 调用失败: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def create_embedding(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """
        创建文本向量
        
        Args:
            text: 输入文本
            model: Embedding 模型名称
        
        Returns:
            List[float]: 向量（1536维）
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model or self.embedding_model,
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(
                f"Embedding 创建成功 - "
                f"模型: {model or self.embedding_model}, "
                f"文本长度: {len(text)} 字符, "
                f"向量维度: {len(embedding)}"
            )
            
            return embedding
        
        except Exception as e:
            logger.error(f"OpenAI Embedding 创建失败: {str(e)}")
            raise
    
    async def create_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        批量创建文本向量（自动分批）
        
        Args:
            texts: 文本列表
            model: Embedding 模型名称
            batch_size: 每批次大小
        
        Returns:
            List[List[float]]: 向量列表
        """
        if not texts:
            return []
        
        # 分批处理
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = await self.client.embeddings.create(
                    input=batch,
                    model=model or self.embedding_model,
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
                logger.debug(f"批量 Embedding 创建成功 - 批次: {i//batch_size + 1}, 数量: {len(batch)}")
            
            except Exception as e:
                logger.error(f"批量 Embedding 创建失败 (批次 {i//batch_size + 1}): {str(e)}")
                raise
        
        return embeddings
    
    async def chat_completion_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Chat Completion API 调用（JSON 模式）
        
        Returns:
            Dict: 解析后的 JSON 对象
        """
        import json
        
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            json_mode=True,
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}, 响应: {response}")
            raise
    
    async def analyze_with_prompt(
        self,
        system_prompt: str,
        user_input: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        """
        使用系统提示词分析输入
        
        Args:
            system_prompt: 系统提示词
            user_input: 用户输入
            model: 模型名称
            temperature: 温度参数
            json_mode: 是否使用 JSON 模式
        
        Returns:
            str: 分析结果
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        
        return await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            json_mode=json_mode,
        )
    
    async def parallel_chat_completion(
        self,
        prompts: List[List[Dict[str, str]]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> List[str]:
        """
        并行执行多个 Chat Completion 请求
        
        Args:
            prompts: 多个消息列表
            model: 模型名称
            temperature: 温度参数
        
        Returns:
            List[str]: 响应列表
        """
        tasks = [
            self.chat_completion(messages, model, temperature)
            for messages in prompts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"并行请求 {i} 失败: {str(result)}")
                processed_results.append("")
            else:
                processed_results.append(result)
        
        return processed_results


# 创建全局实例
openai_service = OpenAIService()
