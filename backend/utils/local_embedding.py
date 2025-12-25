"""
本地 Embedding 模型服务
使用 sentence-transformers 替代 OpenAI Embedding API
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np


class LocalEmbeddingService:
    """本地 Embedding 服务"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化本地 Embedding 模型
        
        推荐的中文友好模型：
        - paraphrase-multilingual-MiniLM-L12-v2 (384维，支持50+语言，速度快)
        - distiluse-base-multilingual-cased-v2 (512维，支持15+语言)
        - all-MiniLM-L6-v2 (384维，英文优化，速度最快)
        
        Args:
            model_name: 模型名称，默认使用多语言模型
        """
        print(f"🔄 正在加载本地 Embedding 模型: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        print(f"✅ 模型加载完成，向量维度: {self.embedding_dimension}")
    
    def create_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        创建文本的 Embedding
        
        Args:
            text: 单个文本字符串或文本列表
            
        Returns:
            单个向量或向量列表
        """
        if isinstance(text, str):
            # 单个文本
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        else:
            # 批量文本
            embeddings = self.model.encode(text, convert_to_numpy=True, show_progress_bar=True)
            return embeddings.tolist()
    
    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.embedding_dimension


# 全局单例
_embedding_service = None


def get_embedding_service(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> LocalEmbeddingService:
    """
    获取 Embedding 服务单例
    
    Args:
        model_name: 模型名称
        
    Returns:
        LocalEmbeddingService 实例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = LocalEmbeddingService(model_name)
    return _embedding_service


# 兼容 OpenAI API 的接口
def create_embeddings(texts: Union[str, List[str]], model: str = None) -> dict:
    """
    创建 Embedding（兼容 OpenAI API 格式）
    
    Args:
        texts: 文本或文本列表
        model: 模型名称（可选，本地模型忽略此参数）
        
    Returns:
        符合 OpenAI API 格式的响应
    """
    service = get_embedding_service()
    
    if isinstance(texts, str):
        texts = [texts]
    
    embeddings = service.create_embedding(texts)
    
    # 构造类似 OpenAI API 的响应格式
    return {
        'data': [
            {
                'embedding': emb,
                'index': i,
                'object': 'embedding'
            }
            for i, emb in enumerate(embeddings)
        ],
        'model': 'local-embedding',
        'object': 'list',
        'usage': {
            'prompt_tokens': sum(len(t.split()) for t in texts),
            'total_tokens': sum(len(t.split()) for t in texts)
        }
    }


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("本地 Embedding 模型测试")
    print("=" * 60)
    
    service = get_embedding_service()
    
    # 测试中文
    test_texts = [
        "我是一名Python工程师，擅长后端开发",
        "寻找全栈开发岗位，熟悉React和Django",
        "有5年工作经验的资深开发者"
    ]
    
    print(f"\n测试文本数量: {len(test_texts)}")
    embeddings = service.create_embedding(test_texts)
    
    print(f"生成的向量数量: {len(embeddings)}")
    print(f"向量维度: {len(embeddings[0])}")
    print(f"第一个向量的前10个值: {embeddings[0][:10]}")
    
    # 计算相似度
    from numpy import dot
    from numpy.linalg import norm
    
    def cosine_similarity(a, b):
        return dot(a, b) / (norm(a) * norm(b))
    
    print("\n相似度矩阵:")
    for i, text_i in enumerate(test_texts):
        for j, text_j in enumerate(test_texts):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            print(f"  文本{i+1} vs 文本{j+1}: {sim:.4f}")
    
    print("\n✅ 测试完成！")
