"""
搜索策略智能体
根据候选人信息和偏好，规划多路径搜索策略
"""
import json
from typing import Dict, Any, List
from loguru import logger

from backend.services.openai_service import openai_service
from backend.config import settings


class SearchStrategy:
    """搜索策略智能体"""
    
    SYSTEM_PROMPT = """你是一位职业搜索策略专家，擅长为求职者规划最优的职位搜索策略。

你的任务是根据候选人的背景和偏好，制定多维度的搜索策略：

1. **搜索路径**：
   - 主路径：最匹配候选人背景的职位
   - 备选路径：稍微跨界但有发展潜力的职位
   - 探索路径：创新性的职业可能

2. **搜索参数**：
   - 关键词组合
   - 职位级别范围
   - 薪资范围
   - 地理位置
   - 公司类型（创业/成熟/大厂）

3. **权重分配**：
   - 为7个匹配维度分配权重（总和为1.0）
   - 技能匹配、经验匹配、薪资匹配、地点匹配、文化匹配、成长潜力、稳定性

4. **搜索优先级**：排序搜索路径的优先级

返回 JSON 格式的搜索策略。"""
    
    async def plan_search(
        self,
        candidate_profile: Dict[str, Any],
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        规划搜索策略
        
        Args:
            candidate_profile: 候选人画像（ResumeAnalyzer 分析结果）
            preferences: 用户偏好设置
        
        Returns:
            Dict: 搜索策略
        """
        try:
            user_prompt = f"""候选人信息：
{json.dumps(candidate_profile, ensure_ascii=False, indent=2)}

用户偏好：
{json.dumps(preferences, ensure_ascii=False, indent=2)}

请为该候选人制定搜索策略，返回以下 JSON 格式：
{{
    "search_paths": [
        {{
            "path_name": "主路径",
            "description": "路径描述",
            "priority": 1,
            "keywords": ["关键词1", "关键词2"],
            "job_titles": ["职位名称1", "职位名称2"],
            "experience_range": {{"min": 3, "max": 5}},
            "salary_range": {{"min": 15000, "max": 25000}},
            "locations": ["城市1", "城市2"],
            "company_types": ["类型1", "类型2"]
        }}
    ],
    "dimension_weights": {{
        "skills": 0.25,
        "experience": 0.20,
        "salary": 0.15,
        "location": 0.10,
        "culture": 0.10,
        "growth": 0.10,
        "stability": 0.10
    }},
    "search_radius": "搜索半径（保守/适中/激进）",
    "rationale": "策略制定理由"
}}

要求：
1. 至少提供2-3条搜索路径
2. 权重总和必须为1.0
3. 优先级从1开始（数字越小优先级越高）
4. 根据候选人偏好调整权重"""
            
            response = await openai_service.chat_completion_json(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
            )
            
            # 验证权重总和
            weights = response.get("dimension_weights", {})
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"权重总和不为1.0 ({total_weight})，进行归一化")
                # 归一化
                for key in weights:
                    weights[key] = weights[key] / total_weight
            
            logger.info(f"搜索策略规划完成 - 路径数: {len(response.get('search_paths', []))}")
            
            return response
        
        except Exception as e:
            logger.error(f"搜索策略规划失败: {str(e)}")
            # 返回默认策略
            return self._get_default_strategy(candidate_profile, preferences)
    
    def _get_default_strategy(
        self,
        candidate_profile: Dict[str, Any],
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        获取默认搜索策略（当AI调用失败时）
        
        Returns:
            Dict: 默认策略
        """
        # 提取基本信息
        recommended_positions = candidate_profile.get("recommended_positions", [])
        salary_expectation = candidate_profile.get("salary_expectation", {})
        
        return {
            "search_paths": [
                {
                    "path_name": "主路径",
                    "description": "基于简历推荐的职位",
                    "priority": 1,
                    "keywords": [],
                    "job_titles": recommended_positions,
                    "experience_range": {"min": 0, "max": 10},
                    "salary_range": salary_expectation,
                    "locations": preferences.get("locations", []),
                    "company_types": [],
                }
            ],
            "dimension_weights": settings.DIMENSION_WEIGHTS,
            "search_radius": "适中",
            "rationale": "使用默认策略（AI 调用失败）",
        }


# 创建全局实例
search_strategy = SearchStrategy()
