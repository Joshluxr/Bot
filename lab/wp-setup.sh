#!/bin/sh
set -eu
sleep 8
until wp core is-installed --path=/var/www/html --allow-root 2>/dev/null; do
  wp core install \
    --path=/var/www/html \
    --url=http://localhost:8080 \
    --title="AUTHZ Lab WP" \
    --admin_user=admin \
    --admin_password=admin123 \
    --admin_email=admin@lab.local \
    --skip-email \
    --allow-root
  sleep 3
done
echo "[wp-setup] WordPress ready with admin / admin123"
