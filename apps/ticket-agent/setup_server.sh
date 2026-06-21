#!/bin/bash
# Полная настройка сервера: nginx + webhook + bot как systemd сервисы

# 1. Установи nginx если нет
apt-get install -y -qq nginx

# 2. Nginx конфиг — проксирует /deploy на webhook server, отдаёт сайты из /var/www/concerts
cat > /etc/nginx/sites-available/concert << 'EOF'
server {
    listen 80 default_server;
    server_name _;

    location /deploy {
        proxy_pass http://127.0.0.1:8080/deploy;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        proxy_set_header Content-Type $content_type;
    }

    location /concerts/ {
        root /var/www;
        index index.html;
        try_files $uri $uri/ =404;
    }

    location / {
        root /var/www/html;
        index index.html;
    }
}
EOF

ln -sf /etc/nginx/sites-available/concert /etc/nginx/sites-enabled/concert
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

mkdir -p /var/www/concerts

# 3. Systemd сервис для бота
cat > /etc/systemd/system/concert-bot.service << 'EOF'
[Unit]
Description=Concert Ticket Telegram Bot
After=network.target

[Service]
WorkingDirectory=/opt/concert-agent/apps/ticket-agent
ExecStart=/usr/bin/python3 /opt/concert-agent/apps/ticket-agent/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 4. Systemd сервис для webhook
cat > /etc/systemd/system/concert-webhook.service << 'EOF'
[Unit]
Description=Concert Deploy Webhook Server
After=network.target

[Service]
WorkingDirectory=/opt/concert-agent/apps/ticket-agent
ExecStart=/usr/bin/python3 /opt/concert-agent/apps/ticket-agent/webhook_server.py
Restart=always
RestartSec=5
Environment=WEBHOOK_SECRET=concert-deploy-secret
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 5. Запусти оба сервиса
pkill -f "python3 main.py" || true
pkill -f "webhook_server" || true

systemctl daemon-reload
systemctl enable concert-bot concert-webhook
systemctl start concert-bot concert-webhook

echo ""
echo "✅ Готово!"
echo "Бот: systemctl status concert-bot"
echo "Webhook: systemctl status concert-webhook"
echo "Логи бота: journalctl -u concert-bot -f"
