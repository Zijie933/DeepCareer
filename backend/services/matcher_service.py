"""
智能匹配服务 - 支持快速匹配和精细匹配
"""
from typing import Dict, List, Tuple, Optional, Any
import re

from backend.services.openai_service import OpenAIService
from backend.utils.local_embedding import LocalEmbeddingService
from backend.utils.logger import logger


class MatcherService:
    """智能匹配服务"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self.embedding_service = LocalEmbeddingService()
    
    def fast_match(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        resume_embedding: Optional[List[float]] = None,
        job_embedding: Optional[List[float]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        快速匹配（规则 + Embedding）
        
        Args:
            resume_data: 简历结构化数据
            job_data: 职位结构化数据
            resume_embedding: 简历向量（可选）
            job_embedding: 职位向量（可选）
        
        Returns:
            (总分 0-100, 详细评分)
        """
        logger.info("执行快速匹配")
        
        scores = {}
        details = {}
        
        # 0. 职位方向匹配（最重要！）- 如果方向不匹配，直接大幅降分
        position_score, position_detail = self._match_position_direction(
            resume_data.get('current_position'),
            resume_data.get('job_intention', {}),
            job_data.get('title', '')
        )
        scores['position'] = position_score
        details['position'] = position_detail
        
        # 如果职位方向完全不匹配（<30分），直接返回低分
        if position_score < 30:
            total_score = position_score * 0.5  # 最高15分
            result = {
                'total_score': round(total_score, 2),
                'dimension_scores': scores,
                'details': details,
                'weights': {'position': 1.0},
                'reason': '职位方向不匹配'
            }
            logger.info(f"快速匹配完成（方向不匹配），总分: {total_score:.2f}")
            return total_score, result
        
        # 1. 技能匹配（30%权重）
        # 简历技能可能是嵌套对象或扁平列表，需要统一处理
        resume_skills = self._flatten_skills(resume_data.get('skills', []))
        skill_score, skill_detail = self._match_skills(
            resume_skills,
            job_data.get('required_skills', []),
            job_data.get('preferred_skills', [])
        )
        scores['skills'] = skill_score
        details['skills'] = skill_detail
        
        # 2. 经验匹配（25%权重）
        exp_score, exp_detail = self._match_experience(
            resume_data.get('years_experience'),
            job_data.get('experience_required')
        )
        scores['experience'] = exp_score
        details['experience'] = exp_detail
        
        # 3. 学历匹配（10%权重）
        edu_score, edu_detail = self._match_education(
            resume_data.get('education'),
            job_data.get('education_required')
        )
        scores['education'] = edu_score
        details['education'] = edu_detail
        
        # 4. 语义相似度（15%权重）
        # 注意：embedding 可能是 NumPy 数组，不能直接用 if arr 判断
        has_resume_emb = resume_embedding is not None and (
            hasattr(resume_embedding, '__len__') and len(resume_embedding) > 0
        )
        has_job_emb = job_embedding is not None and (
            hasattr(job_embedding, '__len__') and len(job_embedding) > 0
        )
        
        if has_resume_emb and has_job_emb:
            semantic_score = self._calculate_cosine_similarity(
                resume_embedding,
                job_embedding
            ) * 100
            scores['semantic'] = semantic_score
            details['semantic'] = {'score': semantic_score, 'method': 'embedding'}
        else:
            scores['semantic'] = 50.0
            details['semantic'] = {'score': 50.0, 'method': 'not_available'}
        
        # 5. 计算总分
        # 职位方向和学历是硬性门槛，权重要大
        weights = {
            'position': 0.30,   # 职位方向最重要，30%
            'skills': 0.25,     # 技能匹配 25%
            'experience': 0.20, # 经验匹配 20%
            'education': 0.15,  # 学历匹配 15%（硬性门槛）
            'semantic': 0.10    # 语义相似度 10%
        }
        
        total_score = sum(scores[k] * weights[k] for k in weights)
        
        result = {
            'total_score': round(total_score, 2),
            'dimension_scores': scores,
            'details': details,
            'weights': weights
        }
        
        logger.info(f"快速匹配完成，总分: {total_score:.2f}")
        return total_score, result
    
    def _match_position_direction(
        self,
        current_position: Optional[str],
        job_intention: Optional[Dict],
        job_title: str
    ) -> Tuple[float, Dict]:
        """
        职位方向匹配 - 判断简历方向和职位是否一致
        
        这是最重要的匹配维度！
        后端开发 不应该匹配 产品经理
        """
        if not job_title:
            return 50.0, {'reason': '职位无标题', 'score': 50.0}
        
        # 定义职位类别
        position_categories = {
            '后端开发': ['后端', '服务端', 'java', 'python', 'go', 'golang', 'php', 'c++', 'c#', '.net', 'node', 'spring', 'django', 'flask', 'fastapi'],
            '前端开发': ['前端', 'web', 'h5', 'javascript', 'typescript', 'react', 'vue', 'angular', 'css', 'html', '小程序'],
            '全栈开发': ['全栈', 'full stack', 'fullstack'],
            '移动开发': ['ios', 'android', '移动', 'flutter', 'react native', 'app开发', '客户端'],
            '测试开发': ['测试', 'qa', 'quality', '自动化测试', '测试开发', 'sdet'],
            '运维/DevOps': ['运维', 'devops', 'sre', '系统管理', '云计算', 'k8s', 'docker', 'linux'],
            '数据开发': ['数据', 'etl', 'hadoop', 'spark', 'flink', '数仓', '大数据', 'data engineer'],
            '算法/AI': ['算法', 'ai', '机器学习', '深度学习', 'nlp', 'cv', '推荐', '搜索', 'ml', 'deep learning'],
            '产品经理': ['产品', 'pm', 'product manager', '产品经理', '产品运营'],
            '设计师': ['设计', 'ui', 'ux', '视觉', '交互', '美术'],
            '项目经理': ['项目经理', 'pmo', '项目管理', 'scrum master'],
            '运营': ['运营', '用户运营', '内容运营', '活动运营', '增长'],
            '销售/商务': ['销售', '商务', 'bd', '客户经理'],
            '人力资源': ['hr', '人力', '招聘', '薪酬', 'hrbp'],
            '财务': ['财务', '会计', '审计', '税务'],
            '安全': ['安全', 'security', '渗透', '攻防'],
            '架构师': ['架构', 'architect', '技术专家', '技术总监'],
            'DBA': ['dba', '数据库管理', 'mysql', 'postgresql', 'oracle', 'mongodb'],
        }
        
        def get_category(text: str) -> List[str]:
            """获取文本对应的职位类别"""
            if not text:
                return []
            text_lower = text.lower()
            categories = []
            for category, keywords in position_categories.items():
                for kw in keywords:
                    if kw.lower() in text_lower:
                        categories.append(category)
                        break
            return categories
        
        # 获取简历的职位方向
        resume_categories = set()
        if current_position:
            resume_categories.update(get_category(current_position))
        
        # 从求职意向获取
        if job_intention:
            positions = job_intention.get('positions', [])
            for pos in positions:
                resume_categories.update(get_category(pos))
        
        # 获取职位的类别
        job_categories = set(get_category(job_title))
        
        # 如果无法识别类别
        if not resume_categories:
            return 50.0, {
                'reason': '无法识别简历职位方向',
                'resume_position': current_position,
                'job_title': job_title,
                'score': 50.0
            }
        
        if not job_categories:
            return 50.0, {
                'reason': '无法识别职位类别',
                'resume_position': current_position,
                'job_title': job_title,
                'score': 50.0
            }
        
        # 计算匹配度
        # 完全匹配
        if resume_categories & job_categories:
            return 100.0, {
                'match': True,
                'resume_categories': list(resume_categories),
                'job_categories': list(job_categories),
                'matched': list(resume_categories & job_categories),
                'score': 100.0
            }
        
        # 相关职位（技术类之间有一定相关性）
        tech_categories = {'后端开发', '前端开发', '全栈开发', '移动开发', '测试开发', '运维/DevOps', '数据开发', '算法/AI', '安全', '架构师', 'DBA'}
        non_tech_categories = {'产品经理', '设计师', '项目经理', '运营', '销售/商务', '人力资源', '财务'}
        
        resume_is_tech = bool(resume_categories & tech_categories)
        job_is_tech = bool(job_categories & tech_categories)
        resume_is_non_tech = bool(resume_categories & non_tech_categories)
        job_is_non_tech = bool(job_categories & non_tech_categories)
        
        # 技术转非技术或非技术转技术，严重不匹配
        if (resume_is_tech and job_is_non_tech) or (resume_is_non_tech and job_is_tech):
            return 10.0, {
                'match': False,
                'resume_categories': list(resume_categories),
                'job_categories': list(job_categories),
                'reason': '技术/非技术方向不匹配',
                'score': 10.0
            }
        
        # 同为技术类但不同方向，有一定相关性
        if resume_is_tech and job_is_tech:
            return 60.0, {
                'match': False,
                'resume_categories': list(resume_categories),
                'job_categories': list(job_categories),
                'reason': '同为技术类但方向不同',
                'score': 60.0
            }
        
        # 同为非技术类但不同方向
        if resume_is_non_tech and job_is_non_tech:
            return 40.0, {
                'match': False,
                'resume_categories': list(resume_categories),
                'job_categories': list(job_categories),
                'reason': '同为非技术类但方向不同',
                'score': 40.0
            }
        
        # 其他情况
        return 30.0, {
            'match': False,
            'resume_categories': list(resume_categories),
            'job_categories': list(job_categories),
            'reason': '职位方向不匹配',
            'score': 30.0
        }
    
    def _flatten_skills(self, skills: Any) -> List[str]:
        """
        将技能数据扁平化为列表
        
        支持格式：
        1. 列表: ["Python", "Java"]
        2. 嵌套对象: {"programming_languages": ["Python"], "frameworks": ["FastAPI"]}
        3. 字符串: "Python, Java, FastAPI"
        """
        if not skills:
            return []
        
        # 已经是列表
        if isinstance(skills, list):
            return [str(s).strip() for s in skills if s]
        
        # 嵌套对象
        if isinstance(skills, dict):
            flat_list = []
            for category, items in skills.items():
                if isinstance(items, list):
                    flat_list.extend([str(s).strip() for s in items if s])
                elif isinstance(items, str):
                    flat_list.append(items.strip())
            return flat_list
        
        # 字符串（逗号分隔）
        if isinstance(skills, str):
            return [s.strip() for s in skills.split(',') if s.strip()]
        
        return []
    
    def _match_skills(
        self,
        resume_skills: List[str],
        required_skills: List[str],
        preferred_skills: List[str] = None
    ) -> Tuple[float, Dict]:
        """
        技能匹配 - 支持模糊匹配
        
        匹配策略：
        1. 精确匹配（忽略大小写）
        2. 包含匹配（React 匹配 React.js）
        3. 别名匹配（K8s 匹配 Kubernetes）
        """
        if not resume_skills:
            return 0.0, {'matched': [], 'missing': required_skills or [], 'reason': '简历无技能数据'}
        
        if not required_skills:
            return 50.0, {'matched': [], 'missing': [], 'reason': '职位无技能要求'}
        
        preferred_skills = preferred_skills or []
        
        # 技能别名映射
        skill_aliases = {
            'k8s': 'kubernetes',
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'react.js': 'react',
            'reactjs': 'react',
            'vue.js': 'vue',
            'vuejs': 'vue',
            'node.js': 'nodejs',
            'node': 'nodejs',
            'pg': 'postgresql',
            'postgres': 'postgresql',
            'mongo': 'mongodb',
            'es': 'elasticsearch',
            'springboot': 'spring boot',
            'spring-boot': 'spring boot',
            'fastapi': 'fast api',
        }
        
        def normalize_skill(skill: str) -> str:
            """标准化技能名称"""
            s = skill.lower().strip()
            return skill_aliases.get(s, s)
        
        def skill_matches(resume_skill: str, job_skill: str) -> bool:
            """检查技能是否匹配"""
            r = normalize_skill(resume_skill)
            j = normalize_skill(job_skill)
            
            # 精确匹配
            if r == j:
                return True
            
            # 包含匹配
            if r in j or j in r:
                return True
            
            # 去除特殊字符后匹配
            r_clean = re.sub(r'[^a-z0-9]', '', r)
            j_clean = re.sub(r'[^a-z0-9]', '', j)
            if r_clean == j_clean:
                return True
            
            return False
        
        # 匹配必备技能
        matched_required = []
        missing_required = []
        
        for req_skill in required_skills:
            found = False
            for res_skill in resume_skills:
                if skill_matches(res_skill, req_skill):
                    matched_required.append(req_skill)
                    found = True
                    break
            if not found:
                missing_required.append(req_skill)
        
        # 匹配加分技能
        matched_preferred = []
        for pref_skill in preferred_skills:
            for res_skill in resume_skills:
                if skill_matches(res_skill, pref_skill):
                    matched_preferred.append(pref_skill)
                    break
        
        # 计算分数
        required_count = len(required_skills)
        preferred_count = len(preferred_skills)
        
        if required_count == 0:
            required_ratio = 1.0
        else:
            required_ratio = len(matched_required) / required_count
        
        if preferred_count == 0:
            preferred_ratio = 0.0
        else:
            preferred_ratio = len(matched_preferred) / preferred_count
        
        # 必备技能占80%，加分技能占20%
        score = required_ratio * 80 + preferred_ratio * 20
        
        return score, {
            'required_match_count': len(matched_required),
            'required_total_count': required_count,
            'preferred_match_count': len(matched_preferred),
            'preferred_total_count': preferred_count,
            'matched_required': matched_required,
            'missing_required': missing_required,
            'matched_preferred': matched_preferred,
            'resume_skills': resume_skills[:20],  # 展示简历技能（最多20个）
            'score': round(score, 2)
        }
    
    def _match_experience(
        self,
        resume_exp: Optional[int],
        job_exp_required: Optional[str]
    ) -> Tuple[float, Dict]:
        """经验匹配"""
        if resume_exp is None:
            return 50.0, {'reason': '简历无工作年限数据', 'score': 50.0}
        
        if not job_exp_required:
            return 80.0, {'reason': '职位无经验要求', 'score': 80.0}
        
        # 解析职位经验要求
        # 支持格式: "3年以上", "3-5年", "5+年", "应届", "不限"
        if '不限' in job_exp_required or '应届' in job_exp_required:
            return 100.0, {
                'resume_years': resume_exp,
                'required': job_exp_required,
                'match': True,
                'score': 100.0
            }
        
        # 提取数字
        numbers = re.findall(r'\d+', job_exp_required)
        if not numbers:
            return 50.0, {'reason': '无法解析经验要求', 'score': 50.0}
        
        if len(numbers) == 1:
            # "3年以上" 或 "3+年"
            required_min = int(numbers[0])
            if resume_exp >= required_min:
                # 满足要求，但也不是越多越好
                if resume_exp <= required_min + 3:
                    score = 100.0
                else:
                    score = max(70.0, 100 - (resume_exp - required_min - 3) * 5)
            else:
                # 不满足
                gap = required_min - resume_exp
                score = max(0, 100 - gap * 20)
        else:
            # "3-5年"
            required_min = int(numbers[0])
            required_max = int(numbers[1])
            if required_min <= resume_exp <= required_max:
                score = 100.0
            elif resume_exp < required_min:
                gap = required_min - resume_exp
                score = max(0, 100 - gap * 20)
            else:
                gap = resume_exp - required_max
                score = max(70, 100 - gap * 10)
        
        return score, {
            'resume_years': resume_exp,
            'required': job_exp_required,
            'match': score >= 80,
            'score': round(score, 2)
        }
    
    def _match_education(
        self,
        resume_edu: Optional[str],
        job_edu_required: Optional[str]
    ) -> Tuple[float, Dict]:
        """学历匹配"""
        edu_levels = {
            '博士': 5,
            '硕士': 4,
            '研究生': 4,
            '本科': 3,
            '学士': 3,
            '专科': 2,
            '大专': 2,
            '高中': 1,
            '不限': 0
        }
        
        if not resume_edu:
            return 50.0, {'reason': '简历无学历数据', 'score': 50.0}
        
        if not job_edu_required or '不限' in job_edu_required:
            return 80.0, {'reason': '职位无学历要求', 'score': 80.0}
        
        # 找到学历等级
        resume_level = 0
        for edu, level in edu_levels.items():
            if edu in resume_edu:
                resume_level = level
                break
        
        required_level = 0
        for edu, level in edu_levels.items():
            if edu in job_edu_required:
                required_level = level
                break
        
        if resume_level >= required_level:
            score = 100.0
        else:
            gap = required_level - resume_level
            score = max(0, 100 - gap * 25)
        
        return score, {
            'resume_education': resume_edu,
            'required_education': job_edu_required,
            'match': resume_level >= required_level,
            'score': round(score, 2)
        }
    
    def _calculate_cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """计算余弦相似度"""
        import numpy as np
        
        # 确保转换为 numpy 数组
        arr1 = np.array(vec1, dtype=np.float64)
        arr2 = np.array(vec2, dtype=np.float64)
        
        # 计算点积和模长
        dot_product = np.dot(arr1, arr2)
        magnitude1 = np.linalg.norm(arr1)
        magnitude2 = np.linalg.norm(arr2)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return float(dot_product / (magnitude1 * magnitude2))
    
    def precise_match(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        resume_text: str,
        job_text: str
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        精细匹配（大模型深度分析）
        
        Args:
            resume_data: 简历结构化数据
            job_data: 职位结构化数据
            resume_text: 简历原文
            job_text: 职位描述原文
        
        Returns:
            (匹配分数 0-100, 分析文本, 详细分析)
        """
        logger.info("执行精细匹配（大模型）")
        
        # 扁平化简历技能用于展示
        flat_skills = self._flatten_skills(resume_data.get('skills', []))
        
        prompt = f"""
你是一位资深的HR和职业顾问，请深度分析以下简历和职位的匹配程度。

**简历信息：**
姓名: {resume_data.get('name', '未知')}
工作年限: {resume_data.get('years_experience', 0)}年
学历: {resume_data.get('education', '未知')}
技能: {', '.join(flat_skills[:15])}
当前职位: {resume_data.get('current_position', '未知')}

**职位要求：**
职位: {job_data.get('title', '未知')}
公司: {job_data.get('company', '未知')}
经验要求: {job_data.get('experience_required', '不限')}
学历要求: {job_data.get('education_required', '不限')}
必备技能: {', '.join(job_data.get('required_skills', [])[:10])}

**请从以下7个维度分析匹配度（每个维度0-100分）：**

1. **技能匹配** (25%)
   - 必备技能覆盖率
   - 技能深度和广度
   - 相关技术栈

2. **经验匹配** (20%)
   - 工作年限是否匹配
   - 行业经验相关性
   - 项目经验质量

3. **薪资期望** (15%)
   - 当前薪资vs职位薪资
   - 涨幅合理性

4. **地理位置** (10%)
   - 是否在同一城市
   - 通勤便利性

5. **文化契合** (10%)
   - 工作方式匹配
   - 价值观契合

6. **成长潜力** (10%)
   - 学习能力
   - 职业发展路径

7. **稳定性** (10%)
   - 跳槽频率
   - 职业稳定性

**输出格式（严格JSON）：**
{{
    "overall_score": 总分(0-100),
    "dimensions": {{
        "skills": 分数,
        "experience": 分数,
        "salary": 分数,
        "location": 分数,
        "culture": 分数,
        "growth": 分数,
        "stability": 分数
    }},
    "strengths": ["优势1", "优势2", "优势3"],
    "weaknesses": ["不足1", "不足2"],
    "recommendation": "推荐建议",
    "summary": "综合评价（2-3句话）"
}}
"""
        
        try:
            response = self.openai_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response['content'].strip()
            # 去除markdown标记
            if content.startswith('```'):
                content = re.sub(r'```json\n|```\n|```', '', content).strip()
            
            import json
            analysis = json.loads(content)
            
            overall_score = analysis.get('overall_score', 0)
            summary = analysis.get('summary', '无法生成分析')
            
            return overall_score, summary, analysis
        
        except Exception as e:
            logger.error(f"精细匹配失败: {e}")
            # 失败回退到快速匹配
            fast_score, fast_details = self.fast_match(resume_data, job_data)
            return fast_score, f"大模型分析失败，使用快速匹配结果: {fast_score}分", {
                'overall_score': fast_score,
                'error': str(e),
                'fallback': True
            }
