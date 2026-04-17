# 在腾讯云终端执行

echo "🔍 检查 .hermes 目录..."
ls -la /root/.hermes/

echo ""
echo "🔍 查找 main.py..."
find /root/.hermes -name "main.py" -type f 2>/dev/null

echo ""
echo "🔍 查找 config.yaml..."
find /root/.hermes -name "config.yaml" -type f 2>/dev/null
