# Recuperação do desenvolvimento

O log de 03/10/2026 mostra que a imagem foi construída e o Django iniciou o comando `migrate`,
mas a autenticação TCP foi recusada para o usuário `erp_dev_admin`. Portanto, nesse teste a
execução passou pelo entrypoint; o bloqueio é a credencial do banco persistido.

## Por que um banco Healthy pode recusar a senha

O healthcheck do serviço `db` usa `pg_isready`, que verifica a disponibilidade do servidor.
Não é uma validação da senha configurada para o Django. Alterar `DB_PASSWORD` no `.env.dev`
também não altera a senha de um usuário já existente no volume PostgreSQL.

Outro caso possível é uma variável `DB_PASSWORD` exportada no shell substituir a interpolação
do serviço `db`, enquanto `web` carrega `.env.dev`. O `erpctl` desta revisão limpa os overrides
de banco, porta e projeto antes de chamar Compose, usando o arquivo do ambiente selecionado.

## Aplicar somente o utilitário para recuperar uma instalação que já existe

Envie o pacote e seu checksum para `~/projetos/compose/erp-dev/`, um nível acima da instalação.
No diretório pai, confira o hash:

```bash
cd ~/projetos/compose/erp-dev
sha256sum -c projeto-erp-v1.3.0-dev.3.tar.gz.sha256
```

Atualize inicialmente somente o utilitário:

```bash
cd ~/projetos/compose/erp-dev/projeto-erp-dev-1.3
cp -p erpctl erpctl.before-dev3
tar -xzf ../projeto-erp-v1.3.0-dev.3.tar.gz \
  --strip-components=1 projeto-erp-dev-1.3/erpctl
chmod 755 . erpctl
./erpctl doctor development
```

O diagnóstico cria um container efêmero, ignora o entrypoint e consulta o PostgreSQL com as
credenciais da aplicação. Não executa migrations, não modifica o banco e não exibe segredos.
O serviço `db` deve estar em execução e a imagem `web` deve já ter sido construída.

## Recuperar uma senha divergente preservando os dados

Abra `.env.dev` no seu editor e identifique o valor efetivo de `DB_PASSWORD`. Confira também
`COMPOSE_PROJECT_NAME=erp-development`, `DB_NAME=erp_dev_db` e `DB_USER=erp_dev_admin`, conforme
o ambiente mostrado no log. Não copie configurações ou credenciais da produção.

Se o diagnóstico indicar falha de senha:

```bash
./erpctl db-password development
```

Esse comando inicia o serviço `db`, cria um `pg_dump` local e usa a conexão via socket dentro
do container para abrir o comando `psql \password`. Digite duas vezes a mesma senha configurada
no `.env.dev`. Ela não é exibida no terminal nem enviada em texto claro em um comando SQL.
Não é necessário conhecer a senha anterior quando a autenticação local permite essa conexão.

Se o backup ou a conexão local falhar, o utilitário interrompe antes de alterar a senha.
Não apague o volume: o usuário ou nome do banco pode ser diferente do configurado no arquivo,
ou a autenticação local pode ter sido personalizada. Nesse caso, envie a mensagem de erro
sem o conteúdo do `.env.dev`.

Confirme a autenticação antes da atualização:

```bash
./erpctl doctor development
```

## Atualizar o restante do pacote

Após o banco autenticar, use o hash que consta no arquivo de checksum:

```bash
erp_package_sha=$(awk '{print $1}' ../projeto-erp-v1.3.0-dev.3.tar.gz.sha256)
./erpctl update development ../projeto-erp-v1.3.0-dev.3.tar.gz "$erp_package_sha"
./erpctl status development
curl -f http://127.0.0.1:8021/health/
```

O healthcheck deverá indicar `environment=development` e `version=1.3.0-dev.3`.
Acesse `http://10.20.0.74:8021/ipam/` para retomar a homologação.

## Permissões do bind mount

O desenvolvimento monta o diretório do host em `/app`. Os modos desse diretório e dos seus
arquivos ficam visíveis no container. O pacote desta revisão normaliza os diretórios para
0755 e o `erpctl` garante acesso à raiz no deploy. O `.env.dev` continua com modo 0600.
O entrypoint também passa a ser instalado em `/usr/local/bin/erp-entrypoint`, fora do mount.

## Referências

- [PostgreSQL 16 — pg_isready](https://www.postgresql.org/docs/16/app-pg-isready.html)
- [PostgreSQL 16 — psql e comando password](https://www.postgresql.org/docs/16/app-psql.html)
- [Imagem oficial PostgreSQL — variáveis de inicialização](https://github.com/docker-library/docs/blob/master/postgres/content.md)
- [Docker Compose — interpolação e precedência do shell](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
