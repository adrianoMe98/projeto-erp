# Continuidade do ERP no Codex

Registro de importação: 30/10/2026. Responsável pelo projeto: Adriano.

## Base importada

O desenvolvimento parte do pacote `projeto-erp-v1.3.0-dev.3.tar.gz`, SHA-256
`df7fb1fa737aa3c681e93c95b29b78abb757ba67c0ac170d9d2a0652a65e2d6b`.
O pacote foi preparado fora do GitHub. Sua importação acumula todas as mudanças desde o
commit original `34b48aa164eaf6fe814c164bc0c3c250c6db441f`, não apenas o IPAM.

A versão é preservada. Esta importação acrescenta o `AGENTS.md`, este documento e os
scripts de preparação e validação para o Codex. A primeira execução no PostgreSQL do
GitHub Actions também identificou um ajuste no bloqueio transacional do IPAM, descrito abaixo.

## Ambientes e branches

- `development`: código importado da `1.3.0-dev.3` para continuar a homologação.
- `main`: código original do repositório, anterior aos pacotes desta conversa.
- Produção no homelab: pacote estável `1.2.0`, em diretório separado, porta 8020.
- Desenvolvimento no homelab: diretório separado, porta 8021.

A produção 1.2.0 ainda não foi sincronizada como uma versão estável no GitHub. Importar o
desenvolvimento não altera os containers nem transforma a `main` em cópia da produção.

## Funcionalidades já implementadas

- Django mantido, com dependências travadas, PostgreSQL no Docker, Gunicorn, WhiteNoise,
  healthcheck, configurações externas e proteções de integridade.
- Login único por usuário ou e-mail, roteamento por perfil, recuperação de senha e temas
  claro/escuro no login, portal e Admin.
- CGNAT determinístico para RouterOS 6, RouterOS 7, iptables e nftables, com scripts e
  relatório PDF visível ao cliente. As regras não são aplicadas automaticamente.
- Pix exclusivamente simulado: QR, webhook autenticado/idempotente e baixa financeira.
  Produção mantém `PIX_ENABLED=0`; não há PSP de pagamentos reais integrado.
- `erpctl` para instalação, atualização com checksum, backup e rollback de código.
  O rollback do código não desfaz migrations nem restaura automaticamente o banco.
- IPAM dedicado em `/ipam/`, com hierarquia IPv4/IPv6, seções, VRFs, pesquisa, ocupação,
  subdivisão limitada, sugestão de espaço livre, mapa limitado e histórico de operações.
- Portal com consulta das redes do próprio cliente, somente leitura.

O phpIPAM é referência de fluxo para a evolução do módulo. Não há paridade completa de
recursos: importação/exportação em massa, descoberta automática e permissões mais granulares
ainda precisam de escopo e implementação.

## Pendência que bloqueava a homologação

O erro inicial de permissão estava associado ao bind mount do diretório dev. A dev.3 ajusta
o acesso à raiz no deploy e instala o entrypoint fora do mount em `/usr/local/bin`.

O último log analisado avançava até `migrate`, mas o PostgreSQL recusava a senha do usuário
`erp_dev_admin`. Não houve confirmação posterior de recuperação no homelab.

Antes de novas alterações na instalação, seguir `docs/RECUPERACAO_DEV.md`: executar
`./erpctl doctor development`, verificar a configuração e, se necessário, usar
`./erpctl db-password development`. Esse comando exige terminal interativo e backup antes
de alterar a senha. Nunca apagar volumes ou copiar credenciais da produção para o dev.

## Preparar o ambiente do Codex

Selecione este repositório e a branch `development`. Use Python 3.12 e configure como
comando de preparação:

```sh
sh scripts/codex-setup.sh
```

Para validar uma tarefa:

```sh
sh scripts/codex-check.sh
```

O setup instala as dependências; não inicia Docker, não executa migrations na instalação do
homelab e não cria administradores. O check usa SQLite local para os testes e não carrega
arquivos de credenciais. A pipeline do GitHub inclui um serviço PostgreSQL 16.

## Evidências e limites

Na preparação da dev.3 foram aprovados 57 testes Django em SQLite e 12 testes de manutenção
com Docker simulado. O registro histórico está em `docs/VALIDACAO.md`.

Na importação foi executado o setup em um ambiente virtual novo com Python 3.12 e as
dependências travadas. O `codex-check.sh` aprovou 57 testes Django, 12 testes de manutenção,
lint, formatação, checks Django, ausência de migrations pendentes e sintaxe dos scripts.
O ambiente publicado na interface do Codex e o resultado do GitHub Actions devem ser
conferidos separadamente. A construção da imagem, a recuperação real da senha e o
comportamento das regras CGNAT nos equipamentos dependem do homelab.

### Ajustes identificados na primeira pipeline

O PostgreSQL não permite aplicar `FOR UPDATE` às relações opcionais trazidas por outer join.
A alocação IPAM passa a bloquear somente a própria sub-rede pai com
`select_for_update(of=("self",))`, mantendo a transação e o carregamento das relações.
O teste existente de alocação atômica cobre esse caso quando executado em PostgreSQL.

Na pipeline, `collectstatic` ocorre antes dos testes para disponibilizar o manifesto usado
com `DEBUG=0`. Apenas a etapa dos testes funcionais HTTP desativa o redirecionamento para
HTTPS. O check de segurança de produção continua com HTTPS obrigatório, cookies seguros e
HSTS habilitados. Não há novas migrations nesses ajustes.

## Próxima tarefa sugerida

Confirmar o healthcheck da dev.3 em `http://IP-DO-HOMELAB:8021/health/` e homologar o IPAM:
hierarquia e subdivisão IPv4/IPv6, VRFs, blocos livres, permissões e isolamento entre clientes.
Registrar os ajustes encontrados em uma branch derivada de `development`, com testes
direcionados, sem promover a linha 1.3 para produção automaticamente.
