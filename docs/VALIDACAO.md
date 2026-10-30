# Registro de validação

## Revisão 1.3.0-dev.3 — 03/10/2026

- 57 testes Django aprovados em SQLite;
- 12 testes de manutenção aprovados com Docker simulado: isolamento do shell, falha de build,
  acesso ao bind mount, senha com backup, diagnóstico sem segredos e instalação com volume antigo;
- checks Django, migrations, lint, formatação e sintaxe POSIX aprovados;
- diretórios do pacote normalizados em 0755; banco, .env, uploads e caches excluídos.

Não havia Docker nem servidor PostgreSQL neste ambiente. O build da nova imagem e a troca de
senha no PostgreSQL real devem ser confirmados no homelab. Os 12 testes de manutenção verificam
o fluxo de comandos; não substituem essa confirmação.

## Histórico de validações anteriores

Validações executadas na preparação deste pacote:

| Verificação | Resultado |
|---|---|
| `ruff check .` | aprovado |
| `ruff format --check .` | aprovado |
| `python manage.py check` | aprovado, sem alertas |
| `python manage.py check --deploy` com HTTPS habilitado | aprovado, sem alertas |
| `python manage.py makemigrations --check --dry-run` | nenhuma migração pendente |
| migração de uma base SQLite vazia | aprovada |
| migration IPAM sobre schema 1.2.0 com sub-rede e endereço existentes | dados e IDs preservados |
| `python manage.py auditar_dados` | aprovado na base de amostra |
| suíte Django | 57 testes aprovados |
| scripts JavaScript de tema | sintaxe validada |
| `erpctl`, `instalar.sh` e `atualizar.sh` | sintaxe POSIX validada |
| ciclo `erpctl` de instalação, atualização e rollback | aprovado com Docker simulado |
| `collectstatic` com armazenamento de produção | concluído |
| healthcheck e página de login via HTTP | aprovados |
| scripts `iptables` e `nftables` | sintaxe POSIX do shell aprovada com `sh -n` |
| relatório CGNAT | PDF A4 renderizado e inspecionado visualmente |

O ambiente de preparação não possuía um daemon Docker nem binários RouterOS/Netfilter. Portanto, a construção da imagem e a aplicação real das regras fazem parte obrigatória do roteiro de homelab. As sintaxes CGNAT foram implementadas com base na documentação oficial citada no `README.md`, mas nenhuma configuração deve ser aplicada diretamente em produção.
