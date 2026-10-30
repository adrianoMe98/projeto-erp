# Release 1.3.0-dev.2

Versão exclusiva para o diretório de desenvolvimento. A produção deve permanecer na versão
estável `1.2.0` até a homologação funcional no homelab.

## Escopo do IPAM

- painel operacional próprio em `/ipam/`;
- hierarquia por cliente, seção, VRF e sub-rede;
- IPv4 e IPv6 sem enumeração de blocos grandes;
- busca, filtros, breadcrumbs e mapa visual;
- próximo prefixo livre e subdivisão em até 256 blocos por operação;
- cadastro do próximo endereço livre;
- gateway, VLAN, equipamento, interface, localização, MAC e responsável;
- histórico das operações feitas pela interface;
- consulta isolada por cliente no portal.

## Endurecimento desta candidata

- o cálculo de bloco livre considera endereços cadastrados diretamente no pai;
- uma sub-rede filha não pode cobrir um endereço já documentado em uma ancestral;
- redes com filhos ou endereços não podem ser redimensionadas de forma inconsistente;
- um bloco com endereços diretos não pode ser convertido em contêiner;
- endereços desativados continuam ocupando sua chave histórica e não são sugeridos novamente;
- a confirmação de subdivisão bloqueia a rede pai no banco durante a alocação;
- o mapa visual marca em azul as faixas delegadas para sub-redes filhas.

## Atualização do ambiente de desenvolvimento

No diretório `erp-dev`, execute:

```bash
./erpctl update development \
  /caminho/projeto-erp-v1.3.0-dev.2.tar.gz \
  SHA256_DO_PACOTE
```

O atualizador preserva `.env.dev`, banco e mídias, cria os backups e executa as migrations na
inicialização. Não use este pacote no diretório de produção.

## Aceite mínimo

1. Abra `/ipam/` com um usuário `staff`.
2. Crie um contêiner IPv4 `/20` e subdivida dois blocos `/24`.
3. Crie um contêiner IPv6 `/32` e subdivida dois blocos `/48`.
4. Cadastre endereços em uma rede pequena e confira o mapa visual.
5. Confirme que uma faixa filha aparece em azul no mapa do bloco pai.
6. Teste busca por prefixo, IP, hostname, VLAN e equipamento.
7. Entre como cliente e confirme acesso somente aos próprios blocos.
