# ERP com Next.js e Supabase — primeira etapa

Esta é a base da reescrita. O Django continua na raiz; não há substituição automática
da instalação do homelab, importação dos dados antigos ou publicação do ambiente.

Implementado: login por e-mail/senha com Supabase Auth, renovação de sessão em cookies,
acesso pendente, saída da conta e lista, busca, paginação, criação e edição de clientes.
O cliente final tem somente consulta ao próprio cadastro. Operadores e administradores
podem cadastrar e editar a carteira. Desative cadastros para preservá-los: a aplicação
não permite exclusão.

## Instalar e executar

Node.js 22 ou superior (validado com Node 24). Na pasta `web`:

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Configure em `.env.local` a URL do projeto de **desenvolvimento** e sua chave pública
publishable (ou anon legada):

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://SEU-PROJETO.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=SUA-CHAVE-PUBLICA
```

Nenhuma chave privilegiada (`service_role` ou `sb_secret_…`) é necessária no aplicativo.
Não coloque essas chaves em variáveis `NEXT_PUBLIC_*`. Sem configuração, o aplicativo
exibe o estado de preparação; não simula autenticação nem inventa cadastros.

## Banco e contas

O schema está em `../supabase/migrations/20261111000000_base_erp.sql`. Aplique-o somente
num projeto Supabase novo de desenvolvimento. Para um projeto hospedado, use o SQL
Editor autenticado ou o fluxo oficial de migrations do Supabase após vincular o destino
correto. Nenhuma migration foi aplicada remotamente por este código.

No Supabase Auth, desative a inscrição pública e crie o usuário da equipe com e-mail
confirmado. As telas do ERP não criam usuários nem definem privilégios. Depois de criar
a conta, um administrador confiável vincula seu UUID no SQL Editor:

```sql
insert into public.perfis (id, nome, papel, cliente_id)
select id, 'Administrador', 'admin', null
from auth.users
where email = 'SEU-EMAIL-ADMINISTRATIVO';
```

Para uma conta de cliente, crie a conta no Auth e um perfil com `papel = 'cliente'` e
`cliente_id` apontando para o cadastro correto. Só faça isso após conferir o vínculo.
Contas sem perfil não têm acesso aos cadastros. Os papéis não vêm de `user_metadata`,
e o usuário comum não pode editar seu próprio papel. As políticas RLS são a proteção
definitiva, inclusive para chamadas diretas à API.

## Supabase local

Na raiz do repositório, com Docker disponível:

```sh
web/node_modules/.bin/supabase start
web/node_modules/.bin/supabase test db
```

O projeto local chama-se `erp-rewrite`, com API na porta 54321 e PostgreSQL na 54322.
Auth, banco e API são necessários; Studio, Storage e Realtime estão desabilitados
nesta etapa. As credenciais geradas pelo CLI são exclusivamente locais. Consulte
`supabase status` sem copiar as chaves privilegiadas para o frontend ou para o Git.
Não execute `db reset`, `db push` ou comandos com `--linked` contra um banco existente
para tentar resolver falhas. Os testes SQL usam transações revertidas.

## Validação

```sh
cd web
npm run check
CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
```

O segundo comando valida os temas claro/escuro e as proteções sem configuração;
execute com `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` vazias.
Se não houver Chromium instalado, use o instalador oficial do Playwright.
As políticas RLS são validadas por `supabase test db`, com usuários distintos.

Para validar login, criação/edição, saída, conta sem perfil e consulta isolada com
Supabase real local, execute após subir o stack:

```sh
CHROMIUM_PATH=/usr/bin/chromium npm run test:integration
```

Esse runner aceita apenas a API local. A chave administrativa local é passada somente
ao processo dos testes para criar e remover suas próprias fixtures; não é gravada
no aplicativo nem usada contra projetos hospedados.

Em máquinas com proxy Docker, o BusyBox wget do container Auth pode ignorar `no_proxy`
e encaminhar o próprio healthcheck de loopback para o proxy. Nesta validação em nuvem,
foi necessário ajustar o wget dos containers de teste para usar conexão local somente
em URLs `127.0.0.1`/`localhost`, preservando o proxy para destinos externos.

O código legado mantém seu próprio setup/check em `scripts/codex-*.sh`.

Validação local em 11/11/2026: build e TypeScript aprovados, 12 testes unitários,
15 testes RLS em PostgreSQL/Supabase local e 5 cenários de navegador (dois sem
configuração e três com Auth/API reais). O Django preservado também aprovou seus
57 testes e 12 testes de manutenção. Não houve validação de um projeto hospedado.

## Próximas etapas

1. Vincular o projeto Supabase escolhido e homologar acessos com a equipe.
2. Migrar IPAM com tipos nativos `cidr`/`inet`, VRFs, hierarquia, alocação transacional
   e as regras de isolamento já existentes no Django.
3. Migrar helpdesk, contratos e financeiro, com testes e plano explícito de importação.
4. Preparar Storage privado para anexos, com políticas por cliente e URLs assinadas.

Storage, recuperação de senha por e-mail, gestão de usuários pela interface, CGNAT,
Pix e importação do legado ainda não foram reescritos. A passagem para produção exige
homologação e um plano de migração dos dados, não apenas a publicação do frontend.
