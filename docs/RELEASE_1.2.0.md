# Release estável 1.2.0

## Objetivo

Esta é a primeira versão preparada para permanecer no ambiente de produção enquanto o próximo
ciclo de funcionalidades evolui separadamente no desenvolvimento.

Não houve mudança funcional entre `1.2.0-rc.1` e `1.2.0`. A promoção conserva o código que passou
pelos testes de produção e desenvolvimento.

## Recursos incluídos

- login único para equipe e clientes;
- portal do cliente com contratos, financeiro, chamados, infraestrutura e relatórios CGNAT;
- geradores CGNAT para RouterOS 6/7, `iptables` e `nftables`;
- tema claro/escuro no login, portal e Admin;
- PostgreSQL, Gunicorn, WhiteNoise e healthcheck;
- atualização versionada com backup e rollback do código;
- ambiente de desenvolvimento separado da produção;
- Pix simulado desativado por padrão na produção.

## Atualização da versão 1.1

A versão 1.1 ainda não possui o comando `erpctl`. Dentro do diretório atual da produção, extraia
primeiro somente o atualizador da versão 1.2.0 e depois deixe que ele faça o backup e a atualização:

```bash
tar -xzf ../projeto-erp-v1.2.0.tar.gz \
  --strip-components=1 \
  projeto-erp-homologacao/erpctl

chmod +x erpctl

./erpctl update production \
  ../projeto-erp-v1.2.0.tar.gz \
  SHA256_DO_PACOTE
```

O comando preserva `.env`, banco PostgreSQL, uploads e volumes. Os backups ficam em
`backups/production/`.

## Instalação nova

```bash
mkdir -p ~/erp/production
tar -xzf projeto-erp-v1.2.0.tar.gz -C ~/erp/production --strip-components=1
cd ~/erp/production
./instalar.sh production IP-OU-DOMINIO
```

Depois crie o administrador:

```bash
docker compose --env-file .env -f compose.yml exec web python manage.py createsuperuser
```

## Verificação após o deploy

```bash
./erpctl version
./erpctl status production
curl -f http://127.0.0.1:8020/health/
./erpctl logs production
```

O endpoint de saúde deve informar a versão `1.2.0` e o ambiente `production`.

## Checklist antes de liberar clientes

- configurar proxy reverso e certificado HTTPS válido;
- ajustar `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS`;
- ativar cookies seguros, redirecionamento HTTPS e HSTS gradualmente;
- configurar SMTP real para recuperação de senha;
- testar restauração do backup em outra VM;
- manter `PIX_ENABLED=0` até integrar um PSP real;
- revisar qualquer script CGNAT antes de aplicá-lo em roteador ou servidor;
- restringir o Admin por VPN, ACL ou rede administrativa quando possível.

## Próximo ciclo

O desenvolvimento seguinte deve partir desta versão como `1.3.0-dev.1`. Apenas funcionalidades
homologadas serão promovidas para uma nova versão estável.
