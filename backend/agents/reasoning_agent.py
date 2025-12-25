"""
推理智能体
生成推荐理由、职业建议、改进方案
"""
import json
from typing import Dict, Any, List
from loguru import logger

from backend.services.openai_service import openai_service


class ReasoningAgent:
    """推理智能体"""
    
    async def explain_match(
        self,
        job_info: Dict[str, Any],
        candidate_profile: Dict[str, Any],
        match_result: Dict[str, Any],
    ) -> str:
        """
        生成推荐理由
        
        Args:
            job_info: 职位信息
            candidate_profile: 候选人画像
            match_result: 匹配结果
        
        Returns:
            str: 推荐理由（200-300字）
        """
        prompt = f"""候选人信息：
{json.dumps(candidate_profile, ensure_ascii=False, indent=2)}

职位信息：
{json.dumps(job_info, ensure_ascii=False, indent=2)}

匹配结果：
{json.dumps(match_result, ensure_ascii=False, indent=2)}

请生成一段专业的推荐理由（200-300字），包括：
1. 为什么推荐这个职位
2. 候选人的优势在哪里
3. 需要注意的短板
4. 职业发展建议

要求：
- 语言专业、客观
- 突出亮点
- 诚实指出不足
- 给出实用建议"""
        
        try:
            response = await openai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            
            logger.info("推荐理由生成成功")
            return response
        
        except Exception as e:
            logger.error(f"推荐理由生成失败: {str(e)}")
            return "推荐理由生成失败，请稍后重试。"
    
    async def suggest_improvements(
        self,
        candidate_profile: Dict[str, Any],
        match_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        生成改进建议
        
        Args:
            candidate_profile: 候选人画像
            match_results: 多个职位的匹配结果
        
        Returns:
            Dict: {
                "skill_gaps": ["需要学习的技能"],
                "experience_suggestions": ["经验提升建议"],
                "resume_improvements": ["简历优化建议"],
                "career_advice": ["职业发展建议"],
            }
        """
        # 提取所有缺失技能
        all_missing_skills = set()
        for result in match_results:
            dimensions = result.get("dimensions", {})
            skills_dim = dimensions.get("skills", {})
            missing = skills_dim.get("missing_skills", [])
            all_missing_skills.update(missing)
        
        prompt = f"""候选人信息：
{json.dumps(candidate_profile, ensure_ascii=False, indent=2)}

目标职位的匹配结果：
{json.dumps(match_results[:3], ensure_ascii=False, indent=2)}

常见缺失技能：
{json.dumps(list(all_missing_skills), ensure_ascii=False)}

请生成改进建议，返回以下 JSON 格式：
{{
    "skill_gaps": ["需要学习的技能1", "技能2"],
    "experience_suggestions": ["经验提升建议1", "建议2"],
    "resume_improvements": ["简历优化建议1", "建议2"],
    "career_advice": ["职业发展建议1", "建议2"]
}}

要求：
1. 建议要具体可执行
2. 优先级从高到低排序
3. 每个类别3-5条建议"""
        
        try:
            response = await openai_service.chat_completion_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            
            logger.info("改进建议生成成功")
            return response
        
        except Exception as e:
            logger.error(f"改进建议生成失败: {str(e)}")
            return {
                "skill_gaps": [],
                "experience_suggestions": [],
                "resume_improvements": [],
                "career_advice": [],
            }
    
    async def generate_cover_letter(
        self,
        job_info: Dict[str, Any],
        candidate_profile: Dict[str, Any],
    ) -> str:
        """
        生成求职信
        
        Args:
            job_info: 职位信息
            candidate_profile: 候选人画像
        
        Returns:
            str: 求职信
        """
        prompt = f"""候选人信息：
{json.dumps(candidate_profile, ensure_ascii=False, indent=2)}

目标职位：
{json.dumps(job_info, ensure_ascii=False, indent=2)}

请为该候选人生成一封专业的求职信（500-800字），包括：
1. 开场白：表达对职位的兴趣
2. 个人优势：结合职位要求展示匹配点
3. 项目经验：突出相关项目成果
4. 职业规划：说明为何选择这个职位
5. 结尾：表达期待

要求：
- 真诚、专业
- 突出候选人的独特价值
- 体现对公司和职位的了解
- 避免空洞套话"""
        
        try:
            response = await openai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
            )
            
            logger.info("求职信生成成功")
            return response
        
        except Exception as e:
            logger.error(f"求职信生成失败: {str(e)}")
            return "求职信生成失败，请稍后重试。"


# 创建全局实例
reasoning_agent = ReasoningAgent()
