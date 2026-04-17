#!/bin/bash
# 解压并对比两个版本

echo "📦 解压两个版本..."

cd /root

# 解压 200symbols 版本
echo "解压 crypto-bot-200symbols.tar.gz..."
mkdir -p crypto-bot-200symbols
tar -xzf crypto-bot-200symbols.tar.gz -C crypto-bot-200symbols/

# 解压 lana-optimized 版本
echo "解压 crypto-bot-lana-optimized.tar.gz..."
mkdir -p crypto-bot-lana-optimized
tar -xzf crypto-bot-lana-optimized.tar.gz -C crypto-bot-lana-optimized/

echo ""
echo "✅ 解压完成！"
echo ""
echo "=== crypto-bot-200symbols 内容 ==="
ls -la crypto-bot-200symbols/
echo ""
echo "=== crypto-bot-lana-optimized 内容 ==="
ls -la crypto-bot-lana-optimized/

echo ""
echo "🔍 检查关键文件..."
echo ""
echo "=== 200symbols 的 config.yaml ==="
if [ -f crypto-bot-200symbols/config.yaml ]; then
    head -10 crypto-bot-200symbols/config.yaml
else
    echo "❌ 文件不存在"
fi

echo ""
echo "=== lana-optimized 的 config.yaml ==="
if [ -f crypto-bot-lana-optimized/config.yaml ]; then
    head -10 crypto-bot-lana-optimized/config.yaml
else
    echo "❌ 文件不存在"
fi

echo ""
echo "=== 200symbols 的 main.py 监控数量 ==="
if [ -f crypto-bot-200symbols/main.py ]; then
    grep "max_symbols" crypto-bot-200symbols/main.py || echo "未找到"
else
    echo "❌ 文件不存在"
fi

echo ""
echo "=== lana-optimized 的 main.py 监控数量 ==="
if [ -f crypto-bot-lana-optimized/main.py ]; then
    grep "max_symbols" crypto-bot-lana-optimized/main.py || echo "未找到"
else
    echo "❌ 文件不存在"
fi
