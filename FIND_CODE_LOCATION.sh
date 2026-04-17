# 在腾讯云终端执行这些命令，找到代码位置

echo "🔍 查找代码位置..."
echo ""
echo "=== 方法 1: 查找所有可能的目录 ==="
find /root -name "main.py" -type f 2>/dev/null | head -10

echo ""
echo "=== 方法 2: 列出 /root 下所有目录 ==="
ls -la /root/

echo ""
echo "=== 方法 3: 查找包含 crypto 的目录 ==="
find /root -type d -name "*crypto*" 2>/dev/null

echo ""
echo "=== 方法 4: 查找最近的 tar.gz 文件 ==="
ls -lht /root/*.tar.gz 2>/dev/null | head -5
