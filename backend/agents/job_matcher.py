"""
职位匹配智能体
7维度智能匹配职位与候选人
"""
import json
from typing import Dict, Any, List
from loguru import logger

from backend.services.openai_service import openai_service
from backend.models.job_v2 import JobV2 as Job


class JobMatcher:
    """职位匹配智能体"""
    
    SYSTEM_PROMPT = """你是一位职位匹配专家，擅长评估候选人与职位的匹配度。

你需要从以下7个维度评估匹配度（每个维度0-100分）：

1. **技能匹配 (Skills Match)**：候选人技能与职位要求的契合度
2. **经验匹配 (Experience Match)**：工作年限、行业经验、项目经验的匹配度
3. **薪资匹配 (Salary Match)**：薪资预期与职位薪资的契合度
4. **地点匹配 (Location Match)**：工作地点的便利性
5. **文化匹配 (Culture Match)**：候选人特质与公司文化的契合度
6. **成长潜力 (Growth Potential)**：职位对候选人职业发展的价值
7. **稳定性风险 (Stability Risk)**：候选人能否稳定胜任该职位（分数越高风险越低）

对于每个维度，给出评分和详细理由。

返回 JSON 格式的匹配结果。"""
    
    async def match(
        self,
        job: Job,
        candidate_profile: Dict[str, Any],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        匹配单个职位
        
        Args:
            job: 职位对象
            candidate_profile: 候选人画像
            weights: 7维度权重
        
        Returns:
            Dict: 匹配结果
        """
        try:
            # 构建职位信息
            job_info = {
                "title": job.title,
                "company": job.company_name,
                "salary": f"{job.salary_min}-{job.salary_max}" if job.salary_min else job.salary_text,
                "location": f"{job.city} {job.district or ''}".strip(),
                "experience_required": job.experience_required,
                "education_required": job.education_required,
                "description": job.description,
                "requirements": job.requirements,
                "skills": job.skills,
                "company_size": job.company_size,
                "company_industry": job.company_industry,
            }
            
            user_prompt = f"""候选人信息：
{json.dumps(candidate_profile, ensure_ascii=False, indent=2)}

职位信息：
{json.dumps(job_info, ensure_ascii=False, indent=2)}

维度权重：
{json.dumps(weights, ensure_ascii=False, indent=2)}

请评估匹配度，返回以下 JSON 格式：
{{
    "overall_score": 综合得分（0-100，根据权重计算）,
    "dimensions": {{
        "skills": {{
            "score": 分数（0-100）,
            "reason": "评分理由",
            "matched_skills": ["匹配的技能"],
            "missing_skills": ["缺失的技能"]
        }},
        "experience": {{
            "score": 分数（0-100）,
            "reason": "评分理由"
        }},
        "salary": {{
            "score": 分数（0-100）,
            "reason": "评分理由"
        }},
        "location": {{
            "score": 分数（0-100）,
            "reason": "评分理由"
        }},
        "culture": {{
            "score": 分数（0-100）,
            "reason": "评分理由"
        }},
        "growth": {{
            "score": 分数（0-100）,
            "reason": "评分理由"
        }},
        "stability": {{
            "score": 分数（0-100）,
            "reason": "评分理由",
            "risks": ["潜在风险"]
        }}
    }},
    "summary": "综合评价（2-3句话）",
    "recommendation": "推荐建议（申请/观望/不推荐）"
}}

要求：
1. 评分要客观准确
2. 理由要具体详细
3. 综合得分 = Σ(维度分数 × 权重)"""
            
            response = await openai_service.chat_completion_json(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            
            # 验证综合得分
            dimensions = response.get("dimensions", {})
            calculated_score = sum(
                dimensions.get(dim, {}).get("score", 0) * weights.get(dim, 0)
                for dim in weights.keys()
            )
            
            # 如果差异过大，使用计算值
            if abs(response.get("overall_score", 0) - calculated_score) > 5:
                logger.warning(f"综合得分与计算值差异过大，使用计算值: {calculated_score}")
                response["overall_score"] = round(calculated_score, 2)
            
            logger.info(f"职位匹配完成 - 职位: {job.title}, 综合得分: {response['overall_score']}")
            
            return response
        
        except Exception as e:
            logger.error(f"职位匹配失败 (job_id={job.id}): {str(e)}")
            return self._get_default_match_result()
    
    async def batch_match(
        self,
        jobs: List[Job],
        candidate_profile: Dict[str, Any],
        weights: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        批量匹配职位
        
        Args:
            jobs: 职位列表
            candidate_profile: 候选人画像
            weights: 7维度权重
        
        Returns:
            List[Dict]: 匹配结果列表
        """
        import asyncio
        
        tasks = [
            self.match(job, candidate_profile, weights)
            for job in jobs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量匹配失败 (job_id={jobs[i].id}): {str(result)}")
                processed_results.append(self._get_default_match_result())
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _get_default_match_result(self) -> Dict[str, Any]:
        """获取默认匹配结果（失败时使用）"""
        return {
            "overall_score": 0,
            "dimensions": {},
            "summary": "匹配分析失败",
            "recommendation": "无法评估",
        }


# 创建全局实例
job_matcher = JobMatcher()
