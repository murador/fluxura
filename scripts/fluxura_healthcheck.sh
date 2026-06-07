#!/bin/bash

echo "===================================="
echo "   🔍 FLUXURA DOCKER HEALTH CHECK"
echo "===================================="

echo ""
echo "📦 CONTAINER STATUS"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "===================================="
echo "📊 CELERY WORKER PING"
echo "===================================="

docker exec fluxura-worker celery -A fluxura.celery_app inspect ping 2>/dev/null || \
echo "⚠️ Celery ping fallito (verifica nome app o worker)"

echo ""
echo "===================================="
echo "📜 WORKER LOG (ultime 20 righe)"
echo "===================================="

docker logs --tail 20 fluxura-worker 2>/dev/null

echo ""
echo "===================================="
echo "🐘 POSTGRES DATABASE CHECK"
echo "===================================="

docker exec fluxura_postgres_1 psql -U postgres -c "\l" 2>/dev/null || \
echo "⚠️ PostgreSQL non raggiungibile o credenziali errate"

echo ""
echo "===================================="
echo "🐇 RABBITMQ STATUS (basic check)"
echo "===================================="

docker exec fluxura_rabbitmq_1 rabbitmqctl status 2>/dev/null | head -n 20 || \
echo "⚠️ RabbitMQ non raggiungibile"

echo ""
echo "===================================="
echo "📈 FLOWER STATUS CHECK"
echo "===================================="

curl -s http://localhost:5555 > /dev/null && echo "✅ Flower UP (port 5555)" || \
echo "⚠️ Flower non raggiungibile"

echo ""
echo "===================================="
echo "🧠 REDIS CHECK"
echo "===================================="

docker exec fluxura_redis_1 redis-cli ping 2>/dev/null || \
echo "⚠️ Redis non raggiungibile"

echo ""
echo "===================================="
echo "🏁 CHECK COMPLETATO"
echo "===================================="
