#!/bin/bash
echo "🚀 Iniciando atualização do ERP..."

# 1. Baixa o código mais recente do GitHub
git pull origin main

# 2. Aplica qualquer alteração de banco de dados que você tenha feito
docker compose exec web python manage.py migrate

# 3. Coleta arquivos estáticos (CSS/JS) novos, se houver
docker compose exec web python manage.py collectstatic --noinput

# 4. Reinicia o container web para carregar o código novo
docker compose restart web

echo "✅ Sistema atualizado com sucesso!"