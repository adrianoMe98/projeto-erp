# Produção, desenvolvimento e atualizações

## Estratégia

O ERP usa um único código e dois ambientes isolados. Não mantenha duas cópias editadas
manualmente: mudanças aprovadas no desenvolvimento devem virar um pacote versionado e só então
ser instaladas na produção.

| Item | Produção | Desenvolvimento |
|---|---|---|
| Arquivo de configuração | `.env` | `.env.dev` |
| Compose | `compose.yml` | `compose.dev.yml` |
| Projeto Compose padrão | `erp-production` | `erp-development` |
| Porta padrão | `8020` | `8021` |
| Servidor Django | Gunicorn | `runserver` com recarga |
| `DEBUG` | desativado | ativado |
| Pix simulado | desativado | ativado |
| Banco e volumes | exclusivos | exclusivos |

Os dois ambientes podem rodar no mesmo host porque usam projetos, portas e volumes separados.
Para manter também versões diferentes do código, extraia cada um em seu próprio diretório, por
exemplo `~/erp/production/` e `~/erp/development/`. Não execute os dois a partir da mesma pasta.

Para atender clientes, a opção mais segura é manter a produção em uma VM própria e o
desenvolvimento em outra VM ou VLAN de laboratório.

## Instalação simplificada

Produção:

```bash
mkdir -p ~/erp/production
tar -xzf projeto-erp-VERSAO.tar.gz -C ~/erp/production --strip-components=1
cd ~/erp/production
./instalar.sh production 192.168.1.50
```

Desenvolvimento:

```bash
mkdir -p ~/erp/development
tar -xzf projeto-erp-VERSAO.tar.gz -C ~/erp/development --strip-components=1
cd ~/erp/development
./instalar.sh development 192.168.1.50
```

O endereço é opcional. Quando omitido, o instalador tenta detectar o primeiro IPv4 do servidor.
Na primeira execução ele:

1. cria `.env` ou `.env.dev` a partir do modelo correspondente;
2. gera chaves aleatórias para Django, PostgreSQL e simulador Pix;
3. protege o arquivo com permissão `600`;
4. constrói as imagens e inicia os containers;
5. espera o healthcheck confirmar aplicação e banco.

Depois crie o administrador no ambiente desejado:

```bash
docker compose --env-file .env -f compose.yml exec web python manage.py createsuperuser
docker compose --env-file .env.dev -f compose.dev.yml exec web python manage.py createsuperuser
```

## Atualização por pacote

Teste primeiro no desenvolvimento:

```bash
./erpctl update development ../projeto-erp-VERSAO.tar.gz SHA256_DO_PACOTE
```

Após o aceite, instale a mesma versão estável na produção:

```bash
./erpctl update production ../projeto-erp-VERSAO.tar.gz SHA256_DO_PACOTE
```

O SHA-256 é opcional, mas recomendado. Durante a atualização, o `erpctl`:

1. valida o pacote e o hash informado;
2. cria backup SQL do banco;
3. cria snapshot do código atual;
4. aplica somente o código, preservando `.env`, `.env.dev`, banco e uploads;
5. reconstrói a imagem, aplica migrações e inicia o serviço;
6. aguarda o healthcheck;
7. restaura automaticamente o código anterior se o serviço não ficar saudável.

Os backups ficam em `backups/production/` ou `backups/development/`.

Migrações do banco não são revertidas automaticamente. Antes de uma versão que remova ou transforme
dados, deve existir um procedimento de reversão específico e um teste de restauração.

## Operações comuns

```bash
./erpctl version
./erpctl status production
./erpctl logs production
./erpctl backup production
./erpctl stop development
```

Para restaurar um snapshot de código criado pelo atualizador:

```bash
./erpctl rollback production backups/production/source-AAAAmmdd-HHMMSS-PID.tar.gz
```

O rollback cria antes um novo backup preventivo do banco e não apaga volumes.

## Fluxo de versões recomendado

- `main`: versão estável que pode ir para clientes;
- `develop`: integração do que está sendo homologado;
- `feature/nome`: desenvolvimento de uma funcionalidade;
- `v1.2.0`: versão estável;
- `v1.3.0-dev.1`: primeira candidata do novo IPAM;
- `v1.3.0-dev.2`: candidata endurecida para homologação do IPAM;
- `v1.3.0-rc.1`: futura candidata para homologação.

O banco de desenvolvimento não deve ser copiado para produção. A promoção transfere o pacote de
código versionado; dados reais permanecem somente no ambiente de produção.

### Primeira atualização a partir da versão 1.1

A versão 1.1 ainda não possui o `erpctl`. Para a primeira transição, extraia a nova versão sobre o
diretório atual, preservando o `.env`, e execute o atualizador de compatibilidade:

```bash
cd ~/erp/production
tar -xzf ../projeto-erp-VERSAO.tar.gz --strip-components=1
./atualizar.sh
```

Depois dessa transição, use sempre `./erpctl update ...`, que também mantém snapshot do código.

## Antes de abrir a produção aos clientes

- publicar atrás de proxy HTTPS com certificado válido;
- definir domínio definitivo e origens CSRF;
- configurar SMTP real para recuperação de senha;
- testar backup e restauração em outra VM;
- manter `PIX_ENABLED=0` até integrar um PSP real;
- validar os scripts CGNAT em roteador ou namespace isolado;
- restringir o Admin por VPN, ACL ou rede administrativa sempre que possível.
