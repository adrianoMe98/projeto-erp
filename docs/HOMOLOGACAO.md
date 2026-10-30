# Roteiro de homologação

## 1. Preparar o servidor

Use uma VM ou host separado da produção. Reserve espaço para o volume do PostgreSQL e confirme que as portas externas escolhidas não estão em uso.

Para testar novidades sem tocar na produção, instale o ambiente de desenvolvimento:

```bash
./instalar.sh development IP-DO-SERVIDOR
```

Ele usa `.env.dev`, porta `8021` e volumes separados. Consulte
`docs/AMBIENTES_E_ATUALIZACOES.md` para o fluxo completo de promoção e rollback.

```bash
cp .env.example .env
chmod 600 .env
```

No `.env`:

- gere valores exclusivos para `DJANGO_SECRET_KEY`, `DB_PASSWORD` e `PIX_SIMULATOR_WEBHOOK_TOKEN`;
- informe o IP e/ou domínio em `DJANGO_ALLOWED_HOSTS`;
- informe a origem completa, incluindo protocolo e porta, em `DJANGO_CSRF_TRUSTED_ORIGINS`;
- deixe as opções de HTTPS em `0` enquanto o acesso for HTTP no laboratório;
- atrás de um proxy HTTPS, habilite cookies seguros e redirecionamento somente após testar o cabeçalho `X-Forwarded-Proto`.

## 2. Instalação nova

```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose ps
```

Validações iniciais:

```bash
curl -f http://127.0.0.1:8020/health/
docker compose logs --tail=100 web
docker compose exec web python manage.py shell -c \
  "from django.contrib.staticfiles.storage import staticfiles_storage; print(staticfiles_storage.url('vendor/bootswatch'))"
```

O último comando deve imprimir `/static/vendor/bootswatch`. Ele valida a compatibilidade entre
o Jazzmin e o armazenamento de arquivos estáticos usado com `DJANGO_DEBUG=0`.

No painel administrativo, cadastre nesta ordem:

1. usuário;
2. cliente;
3. perfil do cliente, vinculando ambos;
4. perfil financeiro e demais recursos.

O login central é `/login/`. Contas com `is_staff` seguem para o painel administrativo; contas com perfil de cliente seguem para o portal.

## 3. Base de dados existente

Não aplique as novas migrações sem auditar os dados antigos. Primeiro faça um `pg_dump` verificável e guarde uma cópia fora do servidor.

Defina temporariamente `DJANGO_AUTO_MIGRATE=0` no `.env` e execute:

```bash
docker compose up -d db
docker compose build web
docker compose run --rm web python manage.py auditar_dados
```

Se a auditoria apontar duplicidades ou vínculos entre clientes diferentes, corrija-os antes de continuar. Com a auditoria limpa:

```bash
docker compose run --rm web python manage.py migrate --plan
docker compose run --rm web python manage.py migrate
```

Volte `DJANGO_AUTO_MIGRATE=1` e inicie o serviço:

```bash
docker compose up -d
```

O script `./atualizar.sh` também cria um dump antes de reconstruir o serviço, mas ele não substitui backup externo nem teste de restauração.

## 4. Homologar o CGNAT

Em **Administração > Planos CGNAT**, crie um plano com:

- rede privada integralmente dentro de `100.64.0.0/10`;
- bloco público IPv4 realmente roteado no laboratório;
- faixa e quantidade de portas por assinante;
- interface de saída exatamente como existe no roteador;
- limite reduzido de assinantes para o primeiro teste.

Na lista de planos, use as ações para gerar RouterOS 6, RouterOS 7, `iptables`, `nftables` ou todas as plataformas. O script é restrito à equipe administrativa. O cliente recebe somente o relatório PDF quando `disponivel_cliente` estiver marcado.

Antes de aplicar um script:

1. faça snapshot ou exportação da configuração do roteador;
2. revise endereços, interface, ordem das regras e conflito de cadeias;
3. aplique primeiro em um roteador/namespace isolado;
4. valide TCP, UDP, ICMP, contadores, retorno das rotas e `conntrack`;
5. teste a reaplicação e o procedimento de rollback;
6. só depois aumente a quantidade de assinantes.

Os arquivos Linux gerados são scripts de carga. A persistência no boot deve ser configurada pelo administrador do host após a homologação.

## 5. Homologar o Pix simulado

Crie primeiro um lançamento em **Pagamentos**. Depois crie uma **Cobrança Pix** para o mesmo cliente e com o mesmo valor. O portal exibirá um QR Code claramente identificado como não pagável.

Há três formas de confirmar a cobrança no simulador:

- ação **Simular confirmação de pagamento** na lista administrativa;
- comando `docker compose exec web python manage.py simular_pagamento_pix TXID`;
- webhook local autenticado.

Exemplo de webhook:

```bash
curl -X POST http://127.0.0.1:8021/pagamentos/pix/webhooks/simulador/ \
  -H 'Content-Type: application/json' \
  -H 'X-Simulator-Token: TOKEN-DE-HOMOLOGACAO' \
  -d '{
    "event_id": "teste-001",
    "event_type": "pix.paid",
    "txid": "TXID-DA-COBRANCA",
    "amount": "1500.00"
  }'
```

Reenvie o mesmo `event_id`: a resposta deve indicar que o evento não é novo e não deve duplicar a baixa. Confirme no portal que a cobrança e o lançamento financeiro ficaram pagos.

## 6. Critérios mínimos de aceite

- login por usuário e por e-mail funcionando para administrador e cliente;
- usuário sem perfil recebe uma tela de acesso pendente, sem erro interno;
- um cliente nunca enxerga relatório, Pix ou contrato de outro cliente;
- script CGNAT e PDF contêm o mesmo mapa de IPs e portas;
- webhook com token incorreto é rejeitado;
- reenvio do webhook é idempotente;
- abertura de chamado e saldo de horas funcionam;
- `/health/` responde e os containers permanecem saudáveis;
- backup e restauração foram testados.

## 7. HTTPS para uma etapa posterior

Com proxy reverso e certificado válidos, ajuste:

```dotenv
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_SECURE_COOKIES=1
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_PRELOAD=0
DJANGO_CSRF_TRUSTED_ORIGINS=https://erp.seudominio.local
```

HSTS deve ser ativado de forma gradual. Só habilite `DJANGO_SECURE_HSTS_PRELOAD=1` quando o domínio e todos os subdomínios estiverem definitivamente preparados para HTTPS.
