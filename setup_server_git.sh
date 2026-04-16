#!/bin/bash

# 服务器 Git 部署密钥配置脚本
# 在服务器上运行此脚本来配置安全的 Git 访问

set -e

echo "========================================"
echo "  配置服务器 Git Deploy Key"
echo "========================================"
echo ""

# 生成 SSH 密钥
if [ ! -f ~/.ssh/crypto_deploy ]; then
    echo "生成部署密钥..."
    ssh-keygen -t ed25519 -C "crypto-bot-deploy" -f ~/.ssh/crypto_deploy -N ""
    echo "✓ 密钥生成完成"
else
    echo "✓ 部署密钥已存在"
fi

# 配置 SSH config
if ! grep -q "Host github.com" ~/.ssh/config 2>/dev/null; then
    echo ""
    echo "配置 SSH..."
    cat >> ~/.ssh/config << 'EOF'

# GitHub Deploy Key for crypto-monitor-bot
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/crypto_deploy
    StrictHostKeyChecking no
EOF
    echo "✓ SSH 配置完成"
else
    echo "✓ SSH 已配置"
fi

echo ""
echo "========================================"
echo "  📋 下一步操作"
echo "========================================"
echo ""
echo "1. 复制下面的公钥："
echo ""
cat ~/.ssh/crypto_deploy.pub
echo ""
echo "2. 添加到 GitHub："
echo "   访问: https://github.com/WEIII2020/crypto-monitor-bot/settings/keys"
echo "   点击: Add deploy key"
echo "   Title: crypto-bot-server-deploy"
echo "   Key: (粘贴上面的公钥)"
echo "   ☐ 不要勾选 'Allow write access'"
echo ""
echo "3. 测试连接："
echo "   ssh -T git@github.com"
echo ""
echo "4. 克隆仓库："
echo "   cd ~"
echo "   git clone git@github.com:WEIII2020/crypto-monitor-bot.git"
echo ""
echo "5. 后续更新："
echo "   cd ~/crypto-monitor-bot"
echo "   git pull"
echo "   sudo systemctl restart crypto-monitor"
echo ""
