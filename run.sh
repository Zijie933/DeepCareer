#!/bin/bash

# DeepCareer 启动脚本

echo "=========================================="
echo "  DeepCareer - 智能职位推荐系统"
echo "=========================================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "请复制 .env.example 并配置："
    echo "  cp .env.example .env"
    exit 1
fi

# 检查 OpenAI API Key
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  警告: OpenAI API Key 未配置"
    echo "请在 .env 文件中设置 OPENAI_API_KEY"
fi

echo ""
echo "启动方式："
echo "1. Docker Compose（推荐）"
echo "2. 本地运行"
echo ""
read -p "请选择 (1/2): " choice

case $choice in
    1)
        echo ""
        echo "🐳 使用 Docker Compose 启动..."
        docker-compose up -d
        echo ""
        echo "✅ 服务启动成功！"
        echo ""
        echo "服务地址："
        echo "  - API: http://localhost:8001"
        echo "  - 文档: http://localhost:8001/docs"
        echo ""
        echo "查看日志: docker-compose logs -f app"
        echo "停止服务: docker-compose down"
        ;;
    2)
        echo ""
        echo "🐍 本地运行模式..."
        
        # 检查虚拟环境
        if [ ! -d "venv" ]; then
            echo "创建虚拟环境..."
            python3 -m venv venv
        fi
        
        echo "激活虚拟环境..."
        source venv/bin/activate
        
        echo "安装依赖..."
        pip install -r requirements.txt
        
        echo ""
        echo "⚠️  请确保 PostgreSQL 和 Redis 已启动！"
        read -p "按回车继续..."
        
        echo ""
        echo "启动应用..."
        python -m backend.main
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
