# Instruções para trabalhar no ERP

Estas instruções valem para todo o repositório. A comunicação com Adriano e os textos da
interface devem ser em português do Brasil.

## Estado e fluxo de trabalho

- A linha atual é `1.3.0-dev.3`, importada para `development`. Leia
  `docs/CONTINUIDADE_CODEX.md` antes de retomar o trabalho.
- A produção do homelab usa o pacote estável `1.2.0` em outro diretório. A `main` ainda
  representa o código original anterior aos pacotes; não a trate como cópia dessa produção.
- Derive branches de tarefa de `development` e entregue mudanças por pull request.
  Promoção para estável, merge e deploy dependem do escopo autorizado por Adriano.
- Preserve o histórico de migrations e os dados existentes. Nunca apague volumes para
  resolver falhas de instalação, permissões ou autenticação.

## Preparação e validação

Use Python 3.12. Instale as dependências travadas com:

```sh
sh scripts/codex-setup.sh
```

Valide as mudanças com:

```sh
sh scripts/codex-check.sh
```

O segundo comando usa SQLite local e configurações de teste; não carrega `.env` ou `.env.dev`
nem usa o PostgreSQL do homelab. A pipeline `.github/workflows/quality.yml` também testa em
PostgreSQL 16. Não declare uma execução simulada como validação real do Docker ou do banco.
Para mudanças em modelos, gere migrations e teste a preservação de dados; não edite migrations
já distribuídas. Para UI, confira login, portal e Admin nos dois temas.

## Organização

- `core`: settings, URLs, healthcheck, metadados e arquivos estáticos.
- `gestao`: clientes, contratos e financeiro.
- `helpdesk`: chamados e apontamentos de horas.
- `infraestrutura`: IPAM, IPv4/IPv6, equipamentos, VLANs, seções e VRFs.
- `cgnat`: cálculo, adaptadores de geração e relatório PDF.
- `pagamentos`: Pix simulado e processamento idempotente de webhooks.
- `portal`: login unificado, permissões e acesso do cliente aos próprios dados.
- `erpctl`, `compose*.yml` e `docker/`: instalação e execução no homelab.

## Regras do domínio

- Toda consulta e alteração de dados do cliente deve respeitar seu isolamento. O IPAM do
  cliente é somente leitura nesta versão; ações operacionais exigem permissões adequadas.
- Considere cliente e VRF ao validar prefixos. Preserve hierarquia, pertencimento de IPs,
  restrições de sobreposição e alocação transacional.
- Não enumere espaços IPv6 grandes. Preserve os limites de geração e do mapa visual e use
  cálculos de intervalos/prefixos.
- O CGNAT gera scripts para RouterOS 6/7, iptables e nftables; não os aplica nos equipamentos.
  Mudanças nos geradores precisam de testes de distribuição de IPs/portas e validação em lab.
- O Pix permanece simulado e desativado por padrão em produção. Não emita cobranças reais
  sem a integração autorizada com um PSP, autenticação de webhook e idempotência.

## Configurações e dados

- Nunca versione `.env`, `.env.dev`, credenciais, dumps, bancos, uploads ou backups.
  Os arquivos `.env*.example` contêm apenas exemplos.
- Desenvolvimento e produção usam diretórios, projetos Compose, portas e volumes distintos.
  Use `erpctl` para selecionar o ambiente e evitar interferência de variáveis do terminal.
- Antes de mexer no instalador, leia `docs/RECUPERACAO_DEV.md`. O caso de senha recusada no
  homelab ainda precisa de confirmação do usuário; não registre essa pendência como resolvida.
- Mantenha as dependências travadas e limite mudanças à tarefa solicitada.
