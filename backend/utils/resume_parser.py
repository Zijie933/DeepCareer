"""
简历结构化解析器
方案1: 规则提取（正则表达式 + 关键词匹配）
方案2: 大模型提取（OpenAI GPT）
方案3: 混合方案（推荐）
"""
import re
from typing import Dict, List, Optional
import jieba.analyse


class RuleBasedParser:
    """基于规则的简历解析器（不需要大模型）"""
    
    def __init__(self):
        # 常见技能关键词库
        self.tech_keywords = {
            'languages': ['Python', 'Java', 'JavaScript', 'Go', 'C++', 'C#', 'PHP', 'Ruby', 'Swift', 'Kotlin'],
            'frameworks': ['Django', 'Flask', 'FastAPI', 'Spring', 'React', 'Vue', 'Angular', 'Express'],
            'databases': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server', 'Elasticsearch'],
            'devops': ['Docker', 'Kubernetes', 'Jenkins', 'Git', 'CI/CD', 'AWS', 'Azure', 'Linux'],
            'other': ['微服务', 'RESTful', 'gRPC', '高并发', '分布式', '消息队列', 'Kafka', 'RabbitMQ']
        }
        
        # 学历关键词
        self.education_keywords = ['本科', '硕士', '博士', '学士', '大专', '专科', '研究生']
        
        # 章节标题关键词
        self.section_markers = {
            'skills': ['技能', '专业技能', '技术栈', '掌握技能', '熟悉技能'],
            'experience': ['工作经验', '项目经验', '工作经历', '职业经历', '任职经历'],
            'education': ['教育背景', '教育经历', '学历', '毕业院校'],
            'projects': ['项目经验', '项目经历', '主要项目'],
            'summary': ['个人简介', '自我评价', '个人介绍', '简介']
        }
    
    def extract_basic_info(self, text: str) -> Dict:
        """提取基本信息"""
        info = {
            'name': None,
            'phone': None,
            'email': None,
            'years_experience': 0
        }
        
        # 提取电话
        phone_pattern = r'1[3-9]\d{9}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            info['phone'] = phone_match.group()
        
        # 提取邮箱
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            info['email'] = email_match.group()
        
        # 提取工作年限
        years_patterns = [
            r'(\d+)\s*年.*?工作经验',
            r'(\d+)\s*年.*?经验',
            r'(\d+)\+?\s*years?.*?experience',
        ]
        for pattern in years_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['years_experience'] = int(match.group(1))
                break
        
        return info
    
    def extract_skills(self, text: str) -> List[str]:
        """提取技能列表"""
        skills = []
        
        # 方法1: 从技能关键词库匹配
        text_lower = text.lower()
        for category, keywords in self.tech_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower or keyword in text:
                    if keyword not in skills:
                        skills.append(keyword)
        
        # 方法2: 找到"技能"章节，提取该段落
        for marker in self.section_markers['skills']:
            pattern = f'{marker}[：:](.*?)(?=\n\n|\n[一二三四五六七八九十]|$)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                section_text = match.group(1)
                # 分词提取
                keywords = jieba.analyse.extract_tags(section_text, topK=15)
                skills.extend([k for k in keywords if k not in skills])
                break
        
        return skills
    
    def extract_experience_sections(self, text: str) -> List[Dict]:
        """提取工作经验段落"""
        experiences = []
        
        # 查找"工作经验"章节
        for marker in self.section_markers['experience']:
            # 匹配整个经验章节
            pattern = f'{marker}[：:](.*?)(?=教育背景|项目经验|技能|$)'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            
            if match:
                exp_section = match.group(1)
                
                # 按日期或公司名分割
                # 常见格式: 2020.01 - 2023.05  XX公司  后端工程师
                exp_pattern = r'(\d{4}[.\-/]\d{1,2}.*?(?:\d{4}[.\-/]\d{1,2}|至今))\s*([^\n]+)'
                
                for exp_match in re.finditer(exp_pattern, exp_section):
                    date_range = exp_match.group(1).strip()
                    content = exp_match.group(2).strip()
                    
                    # 提取公司和职位
                    parts = content.split()
                    company = parts[0] if parts else ''
                    position = parts[1] if len(parts) > 1 else ''
                    
                    experiences.append({
                        'date_range': date_range,
                        'company': company,
                        'position': position,
                        'description': content
                    })
                
                break
        
        return experiences
    
    def extract_education(self, text: str) -> Dict:
        """提取教育背景"""
        education = {
            'degree': None,
            'school': None,
            'major': None
        }
        
        # 查找学历关键词
        for degree in self.education_keywords:
            if degree in text:
                education['degree'] = degree
                break
        
        # 查找教育背景章节
        for marker in self.section_markers['education']:
            pattern = f'{marker}[：:](.*?)(?=\n\n|工作经验|项目经验|$)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                edu_text = match.group(1).strip()
                education['school'] = edu_text.split('\n')[0] if edu_text else None
                break
        
        return education
    
    def parse(self, resume_text: str) -> Dict:
        """
        解析简历（规则方法）
        
        Returns:
            {
                'basic_info': {...},
                'skills': [...],
                'experience': [...],
                'education': {...},
                'confidence': 0.85  # 置信度
            }
        """
        result = {
            'basic_info': self.extract_basic_info(resume_text),
            'skills': self.extract_skills(resume_text),
            'experience': self.extract_experience_sections(resume_text),
            'education': self.extract_education(resume_text),
        }
        
        # 计算置信度（根据提取到的字段数量）
        filled_fields = 0
        total_fields = 4
        
        if result['basic_info']['years_experience'] > 0:
            filled_fields += 1
        if len(result['skills']) > 0:
            filled_fields += 1
        if len(result['experience']) > 0:
            filled_fields += 1
        if result['education']['degree']:
            filled_fields += 1
        
        result['confidence'] = filled_fields / total_fields
        
        return result


class LLMParser:
    """基于大模型的简历解析器（需要调用 OpenAI API）"""
    
    def __init__(self, client):
        """
        Args:
            client: OpenAI client 实例
        """
        self.client = client
    
    def parse(self, resume_text: str, model: str = "gpt-4o-mini") -> Dict:
        """
        使用大模型解析简历
        
        Returns:
            {
                'basic_info': {...},
                'skills': [...],
                'experience': [...],
                'education': {...},
                'confidence': 1.0
            }
        """
        prompt = f"""
请分析以下简历，提取结构化信息。请严格按照JSON格式返回，不要有其他说明文字。

简历内容:
{resume_text}

请返回以下JSON格式:
{{
    "basic_info": {{
        "name": "姓名（如果有）",
        "phone": "电话（如果有）",
        "email": "邮箱（如果有）",
        "years_experience": 工作年限数字
    }},
    "skills": ["技能1", "技能2", "技能3"],
    "experience": [
        {{
            "date_range": "时间段",
            "company": "公司名",
            "position": "职位",
            "description": "工作描述"
        }}
    ],
    "education": {{
        "degree": "学历",
        "school": "学校",
        "major": "专业"
    }}
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的简历解析助手，擅长从简历中提取结构化信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 低温度，更确定的输出
                response_format={"type": "json_object"}  # 强制返回JSON
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            result['confidence'] = 1.0  # 大模型置信度高
            
            return result
            
        except Exception as e:
            print(f"❌ 大模型解析失败: {e}")
            return {
                'basic_info': {},
                'skills': [],
                'experience': [],
                'education': {},
                'confidence': 0.0
            }


class HybridParser:
    """混合解析器（推荐）：先用规则，失败时用大模型"""
    
    def __init__(self, openai_client=None):
        self.rule_parser = RuleBasedParser()
        self.llm_parser = LLMParser(openai_client) if openai_client else None
        self.confidence_threshold = 0.6  # 置信度阈值
    
    def parse(self, resume_text: str, force_llm: bool = False) -> Dict:
        """
        混合解析
        
        Args:
            resume_text: 简历文本
            force_llm: 强制使用大模型
        
        Returns:
            解析结果
        """
        # 1. 先用规则解析
        if not force_llm:
            print("🔧 使用规则解析...")
            result = self.rule_parser.parse(resume_text)
            
            print(f"   置信度: {result['confidence']*100:.0f}%")
            
            # 2. 如果置信度足够，直接返回
            if result['confidence'] >= self.confidence_threshold:
                print("✅ 规则解析成功")
                return result
            else:
                print(f"⚠️  规则解析置信度低 ({result['confidence']*100:.0f}%)")
        
        # 3. 置信度不够或强制使用，调用大模型
        if self.llm_parser:
            print("🤖 调用大模型解析...")
            result = self.llm_parser.parse(resume_text)
            print("✅ 大模型解析完成")
            return result
        else:
            print("⚠️  未配置大模型，返回规则解析结果")
            return self.rule_parser.parse(resume_text)


# ============================================================
# 测试代码
# ============================================================
if __name__ == '__main__':
    test_resume = """
    张三
    电话: 13812345678
    邮箱: zhangsan@example.com
    
    个人简介:
    资深Python后端开发工程师，拥有5年互联网开发经验。
    
    专业技能:
    - 精通Python、熟悉Java
    - 熟练使用Django、FastAPI框架
    - 掌握MySQL、PostgreSQL、Redis
    - 了解Docker、Kubernetes容器技术
    - 熟悉RESTful API设计、微服务架构
    
    工作经验:
    2020.03 - 至今  腾讯科技  高级后端工程师
    负责公司核心业务后端服务开发，使用Django框架构建高并发API服务。
    参与微服务架构改造，使用Docker进行容器化部署。
    
    2018.06 - 2020.02  阿里巴巴  后端开发工程师
    负责电商平台后端开发，处理日均百万级请求。
    使用Redis优化缓存，提升系统性能30%。
    
    教育背景:
    2014.09 - 2018.06  清华大学  计算机科学与技术  本科
    """
    
    print("=" * 70)
    print("简历解析器测试")
    print("=" * 70)
    
    # 测试规则解析
    print("\n【测试1: 规则解析】")
    print("-" * 70)
    rule_parser = RuleBasedParser()
    result = rule_parser.parse(test_resume)
    
    print(f"\n基本信息:")
    print(f"  电话: {result['basic_info']['phone']}")
    print(f"  邮箱: {result['basic_info']['email']}")
    print(f"  工作年限: {result['basic_info']['years_experience']}年")
    
    print(f"\n技能列表 ({len(result['skills'])}项):")
    for skill in result['skills'][:10]:
        print(f"  • {skill}")
    
    print(f"\n工作经验 ({len(result['experience'])}段):")
    for exp in result['experience']:
        print(f"  • {exp['date_range']} - {exp['company']}")
    
    print(f"\n教育背景:")
    print(f"  学历: {result['education']['degree']}")
    print(f"  学校: {result['education']['school']}")
    
    print(f"\n置信度: {result['confidence']*100:.0f}%")
    
    print("\n" + "=" * 70)
    print("✅ 规则解析完成！无需调用大模型API，成本为0")
    print("=" * 70)
