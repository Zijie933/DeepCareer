"""
简历分析智能体
深度分析简历，提取技能图谱、职业路径、优劣势等
"""
import json
from typing import Dict, Any
from loguru import logger

from backend.services.openai_service import openai_service


class ResumeAnalyzer:
    """简历分析智能体"""
    
    SYSTEM_PROMPT = """你是一位资深的HR和职业规划专家，擅长深度分析简历。

你的任务是分析候选人的简历，提取以下信息：

1. **基本信息**：姓名、联系方式、求职意向
2. **技能图谱**：
   - 核心技能（hard skills）及熟练度
   - 软技能（soft skills）
   - 技术栈分类（编程语言、框架、工具等）
3. **工作经验分析**：
   - 工作年限
   - 行业经验
   - 职位级别（初级/中级/高级/资深）
   - 项目经验亮点
4. **教育背景**：学历、专业、学校
5. **职业路径**：
   - 当前职业阶段
   - 职业发展方向
   - 潜在转型可能
6. **优势与亮点**：列出候选人的核心竞争力
7. **劣势与短板**：指出可能的不足之处
8. **薪资预期范围**：根据经验推断合理薪资范围（月薪，人民币）
9. **适合的职位类型**：推荐3-5种适合的职位

请以 JSON 格式返回分析结果。"""
    
    JSON_SCHEMA = {
        "basic_info": {
            "name": "候选人姓名",
            "contact": "联系方式",
            "job_intention": "求职意向",
        },
        "skills": {
            "core_skills": [
                {"name": "技能名称", "proficiency": "熟练度（初级/中级/高级/精通）"}
            ],
            "soft_skills": ["技能1", "技能2"],
            "tech_stack": {
                "languages": ["编程语言"],
                "frameworks": ["框架"],
                "tools": ["工具"],
            }
        },
        "experience": {
            "years": "工作年限（数字）",
            "industries": ["行业1", "行业2"],
            "level": "职位级别（初级/中级/高级/资深/专家）",
            "highlights": ["亮点1", "亮点2"],
        },
        "education": {
            "degree": "学历",
            "major": "专业",
            "university": "学校",
        },
        "career_path": {
            "current_stage": "当前职业阶段",
            "development_direction": "职业发展方向",
            "potential_transitions": ["潜在转型方向"],
        },
        "strengths": ["优势1", "优势2"],
        "weaknesses": ["劣势1", "劣势2"],
        "salary_expectation": {
            "min": "最低月薪（元）",
            "max": "最高月薪（元）",
        },
        "recommended_positions": ["职位类型1", "职位类型2"],
    }
    
    async def analyze(self, resume_text: str) -> Dict[str, Any]:
        """
        分析简历
        
        Args:
            resume_text: 简历文本
        
        Returns:
            Dict: 分析结果（JSON）
        """
        try:
            user_prompt = f"""请分析以下简历：

{resume_text}

请按照以下 JSON 格式返回分析结果：
{json.dumps(self.JSON_SCHEMA, ensure_ascii=False, indent=2)}

要求：
1. 尽可能详细和准确
2. 如果某些信息缺失，使用 null 或空数组
3. 薪资预期要合理，基于工作年限和技能水平
4. 推荐职位要契合候选人背景"""
            
            response = await openai_service.chat_completion_json(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # 降低随机性，提高准确性
            )
            
            logger.info(f"简历分析完成 - 候选人: {response.get('basic_info', {}).get('name', 'Unknown')}")
            
            return response
        
        except Exception as e:
            logger.error(f"简历分析失败: {str(e)}")
            raise
    
    async def extract_keywords(self, resume_text: str) -> list[str]:
        """
        提取简历关键词（用于职位匹配）
        
        Args:
            resume_text: 简历文本
        
        Returns:
            List[str]: 关键词列表
        """
        prompt = f"""请从以下简历中提取20-30个最重要的关键词，用于职位匹配。

关键词应包括：
- 技能名称（编程语言、框架、工具）
- 行业术语
- 职位名称
- 项目经验关键词

简历内容：
{resume_text}

请以 JSON 数组格式返回关键词：
{{"keywords": ["关键词1", "关键词2", ...]}}"""
        
        try:
            response = await openai_service.chat_completion_json(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            
            keywords = response.get("keywords", [])
            logger.info(f"关键词提取完成 - 数量: {len(keywords)}")
            
            return keywords
        
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            return []
    
    async def assess_quality(self, resume_text: str) -> Dict[str, Any]:
        """
        评估简历质量
        
        Args:
            resume_text: 简历文本
        
        Returns:
            Dict: {
                "score": 0-100,  # 总分
                "dimensions": {  # 各维度评分
                    "completeness": 0-100,  # 完整性
                    "clarity": 0-100,  # 清晰度
                    "professionalism": 0-100,  # 专业性
                    "relevance": 0-100,  # 相关性
                },
                "suggestions": ["改进建议1", "改进建议2"],
            }
        """
        prompt = f"""请评估以下简历的质量，并给出改进建议。

评估维度：
1. 完整性（是否包含必要信息）
2. 清晰度（表达是否清晰）
3. 专业性（格式、用词是否专业）
4. 相关性（内容是否聚焦目标职位）

简历内容：
{resume_text}

请以 JSON 格式返回评估结果：
{{
    "score": 总分（0-100）,
    "dimensions": {{
        "completeness": 完整性分数（0-100）,
        "clarity": 清晰度分数（0-100）,
        "professionalism": 专业性分数（0-100）,
        "relevance": 相关性分数（0-100）
    }},
    "suggestions": ["改进建议1", "改进建议2"]
}}"""
        
        try:
            response = await openai_service.chat_completion_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            logger.info(f"简历质量评估完成 - 总分: {response.get('score', 0)}")
            
            return response
        
        except Exception as e:
            logger.error(f"简历质量评估失败: {str(e)}")
            return {
                "score": 0,
                "dimensions": {},
                "suggestions": [],
            }


# 创建全局实例
resume_analyzer = ResumeAnalyzer()
