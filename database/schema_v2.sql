-- DeepCareer 数据库架构 V2
-- 支持规则提取和大模型提取两种模式

-- 1. 简历表（增强版）
CREATE TABLE IF NOT EXISTS resumes (
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    user_id VARCHAR(100),
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    
    -- 原始文本
    full_text TEXT,
    
    -- 结构化数据（核心）
    structured_data JSONB NOT NULL DEFAULT '{}',  -- 结构化简历数据
    
    -- 提取元数据
    extraction_method VARCHAR(20) NOT NULL DEFAULT 'rule',  -- 'rule' 或 'llm'
    extraction_confidence FLOAT DEFAULT 0.0,  -- 提取置信度 0-1
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 用户是否已确认/修改
    user_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    
    -- 向量字段
    text_embedding VECTOR(384),  -- 384维 paraphrase-multilingual-MiniLM-L12-v2
    
    -- AI分析结果（可选）
    ai_analysis JSONB,
    quality_score FLOAT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_extraction_method (extraction_method),
    INDEX idx_created_at (created_at)
);

-- 2. 招聘信息表（增强版）
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    
    -- 外部标识
    external_id VARCHAR(100) UNIQUE,
    platform VARCHAR(50),  -- 来源平台
    job_url VARCHAR(500),
    
    -- 基本信息
    title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    city VARCHAR(50),
    district VARCHAR(50),
    
    -- 薪资
    salary_min INTEGER,
    salary_max INTEGER,
    salary_text VARCHAR(100),
    
    -- 要求
    experience_required VARCHAR(50),
    education_required VARCHAR(50),
    
    -- 原始描述
    full_description TEXT,
    
    -- 结构化数据（核心）
    structured_data JSONB NOT NULL DEFAULT '{}',  -- 结构化职位数据
    
    -- 提取元数据
    extraction_method VARCHAR(20) NOT NULL DEFAULT 'rule',  -- 'rule' 或 'llm'
    extraction_confidence FLOAT DEFAULT 0.0,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 向量字段
    description_embedding VECTOR(384),
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    posted_at TIMESTAMP WITH TIME ZONE,
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_platform (platform),
    INDEX idx_city (city),
    INDEX idx_extraction_method (extraction_method),
    INDEX idx_is_active (is_active),
    INDEX idx_posted_at (posted_at)
);

-- 3. 匹配记录表
CREATE TABLE IF NOT EXISTS match_records (
    id SERIAL PRIMARY KEY,
    
    -- 关联
    resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- 匹配方式
    match_method VARCHAR(20) NOT NULL,  -- 'fast' 或 'precise'
    
    -- 快速匹配结果（规则+Embedding）
    fast_score FLOAT,  -- 快速匹配分数 0-100
    fast_details JSONB,  -- 快速匹配详情
    
    -- 精细匹配结果（大模型）
    precise_score FLOAT,  -- 精细匹配分数 0-100
    precise_analysis TEXT,  -- 大模型分析文本
    precise_details JSONB,  -- 大模型分析详情
    
    -- 时间戳
    matched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_resume_id (resume_id),
    INDEX idx_job_id (job_id),
    INDEX idx_match_method (match_method),
    INDEX idx_fast_score (fast_score),
    INDEX idx_precise_score (precise_score),
    UNIQUE INDEX idx_resume_job_method (resume_id, job_id, match_method)
);

-- 4. 结构化字段定义表（用于动态表单）
CREATE TABLE IF NOT EXISTS field_definitions (
    id SERIAL PRIMARY KEY,
    
    -- 字段信息
    category VARCHAR(20) NOT NULL,  -- 'resume' 或 'job'
    field_name VARCHAR(50) NOT NULL,
    field_label VARCHAR(100) NOT NULL,
    field_type VARCHAR(20) NOT NULL,  -- 'text', 'number', 'array', 'date' 等
    
    -- 显示配置
    is_required BOOLEAN DEFAULT FALSE,
    default_value TEXT,
    placeholder TEXT,
    help_text TEXT,
    
    -- 提取规则（用于规则提取）
    extraction_rules JSONB,  -- 正则、关键词等
    
    -- 排序
    sort_order INTEGER DEFAULT 0,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE INDEX idx_category_field (category, field_name)
);

-- 5. 提取缓存表（优化性能）
CREATE TABLE IF NOT EXISTS extraction_cache (
    id SERIAL PRIMARY KEY,
    
    -- 缓存key（原始文本的hash）
    content_hash VARCHAR(64) NOT NULL UNIQUE,
    
    -- 提取结果
    extraction_method VARCHAR(20) NOT NULL,
    structured_data JSONB NOT NULL,
    confidence FLOAT,
    
    -- 统计
    hit_count INTEGER DEFAULT 1,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_hit_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_content_hash (content_hash),
    INDEX idx_hit_count (hit_count)
);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入默认字段定义
INSERT INTO field_definitions (category, field_name, field_label, field_type, is_required, sort_order) VALUES
-- 简历字段 - 基本信息
('resume', 'name', '姓名', 'text', true, 1),
('resume', 'phone', '电话', 'text', true, 2),
('resume', 'email', '邮箱', 'text', true, 3),
('resume', 'age', '年龄', 'number', false, 4),
('resume', 'gender', '性别', 'text', false, 5),
('resume', 'location', '所在城市', 'text', false, 6),
('resume', 'years_experience', '工作年限', 'number', true, 7),
('resume', 'current_position', '当前职位', 'text', false, 8),
('resume', 'current_company', '当前公司', 'text', false, 9),

-- 简历字段 - 教育背景
('resume', 'education_list', '教育经历', 'array', true, 10),
('resume', 'education_list.school', '学校名称', 'text', true, 11),
('resume', 'education_list.major', '专业', 'text', false, 12),
('resume', 'education_list.degree', '学历', 'text', true, 13),
('resume', 'education_list.start_date', '入学时间', 'date', false, 14),
('resume', 'education_list.end_date', '毕业时间', 'date', false, 15),
('resume', 'education_list.gpa', 'GPA', 'text', false, 16),
('resume', 'education_list.achievements', '在校成就', 'text', false, 17),

-- 简历字段 - 工作经历
('resume', 'work_experiences', '工作经历', 'array', true, 20),
('resume', 'work_experiences.company', '公司名称', 'text', true, 21),
('resume', 'work_experiences.position', '职位', 'text', true, 22),
('resume', 'work_experiences.department', '部门', 'text', false, 23),
('resume', 'work_experiences.start_date', '开始时间', 'date', true, 24),
('resume', 'work_experiences.end_date', '结束时间', 'date', false, 25),
('resume', 'work_experiences.location', '工作地点', 'text', false, 26),
('resume', 'work_experiences.responsibilities', '工作职责', 'array', false, 27),
('resume', 'work_experiences.achievements', '业绩成果', 'array', false, 28),

-- 简历字段 - 项目经历
('resume', 'project_experiences', '项目经历', 'array', false, 30),
('resume', 'project_experiences.name', '项目名称', 'text', true, 31),
('resume', 'project_experiences.role', '担任角色', 'text', false, 32),
('resume', 'project_experiences.company', '所属公司', 'text', false, 33),
('resume', 'project_experiences.start_date', '开始时间', 'date', false, 34),
('resume', 'project_experiences.end_date', '结束时间', 'date', false, 35),
('resume', 'project_experiences.tech_stack', '技术栈', 'array', false, 36),
('resume', 'project_experiences.description', '项目描述', 'text', false, 37),
('resume', 'project_experiences.responsibilities', '我的职责', 'array', false, 38),
('resume', 'project_experiences.achievements', '项目成果', 'array', false, 39),

-- 简历字段 - 技能
('resume', 'skills', '技能', 'object', true, 40),
('resume', 'skills.programming_languages', '编程语言', 'array', false, 41),
('resume', 'skills.frameworks', '框架', 'array', false, 42),
('resume', 'skills.databases', '数据库', 'array', false, 43),
('resume', 'skills.tools', '工具/平台', 'array', false, 44),
('resume', 'skills.other', '其他技能', 'array', false, 45),

-- 简历字段 - 证书
('resume', 'certifications', '证书资质', 'array', false, 50),
('resume', 'certifications.name', '证书名称', 'text', true, 51),
('resume', 'certifications.issuer', '颁发机构', 'text', false, 52),
('resume', 'certifications.date', '获得时间', 'date', false, 53),
('resume', 'certifications.credential_id', '证书编号', 'text', false, 54),

-- 简历字段 - 语言能力
('resume', 'languages', '语言能力', 'array', false, 60),
('resume', 'languages.language', '语言', 'text', true, 61),
('resume', 'languages.proficiency', '熟练程度', 'text', true, 62),

-- 简历字段 - 获奖经历
('resume', 'awards', '获奖经历', 'array', false, 70),
('resume', 'awards.name', '奖项名称', 'text', true, 71),
('resume', 'awards.issuer', '颁发机构', 'text', false, 72),
('resume', 'awards.date', '获奖时间', 'date', false, 73),
('resume', 'awards.description', '描述', 'text', false, 74),

-- 简历字段 - 论文/专利
('resume', 'publications', '论文/专利', 'array', false, 80),
('resume', 'publications.title', '标题', 'text', true, 81),
('resume', 'publications.type', '类型', 'text', false, 82),
('resume', 'publications.date', '发表时间', 'date', false, 83),
('resume', 'publications.description', '描述', 'text', false, 84),

-- 简历字段 - 社会活动
('resume', 'social_activities', '社会活动', 'array', false, 90),
('resume', 'social_activities.organization', '组织名称', 'text', true, 91),
('resume', 'social_activities.role', '角色', 'text', false, 92),
('resume', 'social_activities.period', '时间段', 'text', false, 93),
('resume', 'social_activities.description', '描述', 'text', false, 94),

-- 简历字段 - 求职意向
('resume', 'job_intention', '求职意向', 'object', false, 100),
('resume', 'job_intention.positions', '期望职位', 'array', false, 101),
('resume', 'job_intention.industries', '期望行业', 'array', false, 102),
('resume', 'job_intention.cities', '期望城市', 'array', false, 103),
('resume', 'job_intention.salary_min', '期望最低薪资', 'number', false, 104),
('resume', 'job_intention.salary_max', '期望最高薪资', 'number', false, 105),
('resume', 'job_intention.job_type', '工作类型', 'text', false, 106),

-- 简历字段 - 其他
('resume', 'self_evaluation', '自我评价', 'text', false, 110),
('resume', 'links', '相关链接', 'object', false, 120),
('resume', 'links.github', 'GitHub', 'text', false, 121),
('resume', 'links.linkedin', 'LinkedIn', 'text', false, 122),
('resume', 'links.portfolio', '作品集', 'text', false, 123),
('resume', 'links.blog', '博客', 'text', false, 124),

-- 职位字段
('job', 'title', '职位名称', 'text', true, 1),
('job', 'company', '公司名称', 'text', true, 2),
('job', 'city', '工作城市', 'text', true, 3),
('job', 'salary_range', '薪资范围', 'text', true, 4),
('job', 'experience_required', '经验要求', 'text', true, 5),
('job', 'education_required', '学历要求', 'text', true, 6),
('job', 'required_skills', '必备技能', 'array', true, 7),
('job', 'preferred_skills', '加分技能', 'array', false, 8),
('job', 'responsibilities', '岗位职责', 'array', true, 9),
('job', 'benefits', '福利待遇', 'array', false, 10),
('job', 'company_size', '公司规模', 'text', false, 11),
('job', 'company_industry', '公司行业', 'text', false, 12);

COMMENT ON TABLE resumes IS '简历表（支持规则提取和大模型提取）';
COMMENT ON TABLE jobs IS '招聘信息表（支持规则提取和大模型提取）';
COMMENT ON TABLE match_records IS '匹配记录表（支持快速匹配和精细匹配）';
COMMENT ON TABLE field_definitions IS '字段定义表（动态表单配置）';
COMMENT ON TABLE extraction_cache IS '提取缓存表（性能优化）';
