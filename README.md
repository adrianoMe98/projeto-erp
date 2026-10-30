# ERP de Consultoria — desenvolvimento 1.3.0-dev.3

Este pacote é exclusivo para desenvolvimento e homologação da linha 1.3.0. A produção usa o
pacote estável 1.2.0 em outro diretório. A revisão inclui diagnóstico do banco e correções das
permissões de instalação.

## Continuidade no Codex

O desenvolvimento está na branch `development`. Leia [AGENTS.md](AGENTS.md) e o
[registro de continuidade](docs/CONTINUIDADE_CODEX.md) para conhecer a base, os ambientes e
as pendências. Para preparar e validar o ambiente:

```sh
sh scripts/codex-setup.sh
sh scripts/codex-check.sh
```

Esses comandos preparam as dependências e executam checks locais; a instalação do homelab
continua seguindo o roteiro abaixo.

## O que foi incluído

- login único para administradores e clientes, por usuário ou e-mail;
- recuperação de senha e encerramento de sessão somente por `POST`;
- gerador determinístico de CGNAT para MikroTik RouterOS 6/7, Linux `iptables` e `nftables`;
- relatório PDF de alocação CGNAT disponível no portal do cliente;
- cobranças Pix em simulador local, com QR Code, webhook autenticado e idempotência;
- regras de integridade entre clientes, equipamentos, VLANs, sub-redes, chamados e pagamentos;
- auditoria de dados legados antes das novas restrições do banco;
- configuração por variáveis de ambiente, PostgreSQL, Gunicorn, WhiteNoise e healthcheck;
- seleção de tema claro/escuro no portal e no painel administrativo;
- ambientes isolados de produção e desenvolvimento;
- instalação e atualização versionada pelo comando `erpctl`, com backup e rollback do código;
- painel IPAM em `/ipam/`, com árvore IPv4/IPv6, seções, VRFs, busca, ocupação,
  próximo bloco livre e portal somente leitura;
- testes automatizados, lint e pipeline de qualidade.

O Pix desta versão é deliberadamente **simulado e não pagável**. A integração com um PSP real deverá substituir apenas a camada de serviço, preservando os modelos, o portal e a confirmação idempotente.

## Início rápido no homelab

Requisitos: Docker Engine e Docker Compose v2.

```bash
./instalar.sh development 10.20.0.74
docker compose --env-file .env.dev -f compose.dev.yml exec web python manage.py createsuperuser
./erpctl status development
```

A versão estável permanece em `http://IP-DO-SERVIDOR:8020/`. Para esta versão de
desenvolvimento, use `./erpctl install development IP-DO-SERVIDOR` e acesse
`http://IP-DO-SERVIDOR:8021/login/`.

Leia [docs/HOMOLOGACAO.md](docs/HOMOLOGACAO.md) antes de usar uma base existente ou aplicar qualquer configuração de rede. A separação dos ambientes e o processo de atualização estão em [docs/AMBIENTES_E_ATUALIZACOES.md](docs/AMBIENTES_E_ATUALIZACOES.md).

Se o banco recusar a senha, siga [docs/RECUPERACAO_DEV.md](docs/RECUPERACAO_DEV.md).

## Validação local

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py test
python -m unittest discover -s scripts/tests -v
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run
```

## Decisão tecnológica

O projeto permanece em Django. A autenticação, o painel administrativo, o ORM, as migrações e as permissões já cobrem boa parte do domínio; trocar de framework agora aumentaria o risco e o prazo sem resolver um gargalo comprovado. A recomendação é modularizar os provedores externos e reavaliar apenas se surgirem métricas concretas de escala ou requisitos incompatíveis.

## Referências técnicas do CGNAT

- [MikroTik — NAT e exemplo de CGNAT determinístico](https://help.mikrotik.com/docs/spaces/ROS/pages/3211299/NAT)
- [Netfilter — NAT HOWTO, Source NAT](https://www.netfilter.org/documentation/HOWTO/NAT-HOWTO-6.html)
