-- DeepCareer 数据库初始化脚本

-- 创建 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 提示信息
DO $$
BEGIN
    RAISE NOTICE 'DeepCareer 数据库初始化完成！';
    RAISE NOTICE '已启用 pgvector 扩展';
END $$;
