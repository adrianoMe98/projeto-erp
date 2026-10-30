# IPAM 1.3.0-dev.2

Esta versão de desenvolvimento inicia a evolução do IPAM do ERP, usando os fluxos do
phpIPAM como referência funcional. Ela não substitui a versão estável `1.2.0` em produção.

## Modelo de organização

```text
Cliente
└── Seção IPAM (Backbone, Datacenter, Clientes...)
    └── VRF ou tabela padrão
        └── Sub-rede raiz
            └── Sub-redes filhas
                └── Endereços documentados
```

- `Cliente` continua sendo o limite de isolamento dos dados.
- `Seção IPAM` organiza blocos por finalidade.
- `VRF` cria domínios de roteamento independentes. O mesmo prefixo pode existir em VRFs
  diferentes do mesmo cliente.
- `Sub-rede` aceita IPv4 e IPv6, estado, gateway, VLAN, equipamento, interface, localização
  e observações.
- `Endereço IP` aceita hostname, descrição, estado, MAC, responsável e observações.

## Acesso

- Operação: `http://IP-DO-SERVIDOR:8021/ipam/` para usuários `staff`.
- Cliente: acessa os blocos pelo item **Blocos IP (IPAM)** no próprio portal.
- O portal é somente leitura. O cliente não recebe rotas de criação, edição ou subdivisão.
- Consultas de cliente sempre filtram o `cliente_id`; uma tentativa de acessar bloco de outra
  empresa responde `404`.

## Recursos desta entrega

- árvore hierárquica IPv4 e IPv6;
- busca por prefixo, IP, hostname, descrição, VLAN, equipamento e localização;
- filtros por cliente, seção, VRF, família e estado;
- visão de utilização, espaço alocado e espaço livre;
- mapa visual para redes com até 1.024 endereços;
- divisão por prefixo e quantidade, com pré-visualização;
- cálculo do próximo bloco livre sem enumerar todo o espaço IPv6;
- cálculo do próximo endereço livre, pulando sub-redes filhas;
- blocos livres não cobrem endereços já documentados diretamente no bloco pai;
- suporte correto a enlaces IPv4 `/31` e hosts `/32`;
- validação de gateway, hierarquia, cliente, seção, VRF e sobreposição;
- proteção contra redimensionamento que deixe filhos ou endereços fora da rede;
- edição de sub-redes e endereços sem exclusão destrutiva;
- mapa visual identifica as faixas ocupadas por sub-redes filhas;
- histórico das criações, edições e subdivisões realizadas pela tela IPAM;
- link direto do Django Admin para o painel IPAM.

## Regras de integridade

1. Uma sub-rede filha deve estar contida na rede pai.
2. Pai e filha devem pertencer ao mesmo cliente, seção e VRF.
3. Sobreposições sem relação pai/filha são bloqueadas dentro da mesma VRF.
4. Prefixos iguais são permitidos em VRFs diferentes.
5. Gateway e endereços devem pertencer ao bloco selecionado.
6. Em IPv4 até `/30`, rede e broadcast não são atribuíveis. Em `/31`, os dois endereços são
   válidos para ponto a ponto.
7. Endereços de uma sub-rede filha devem ser cadastrados no bloco mais específico.
8. Operações de subdivisão são transacionais e limitadas a 256 blocos por vez.
9. O mapa visual nunca enumera redes com mais de 1.024 endereços.
10. Um endereço desativado permanece reservado no cadastro; para reutilizá-lo, edite o
    registro existente em vez de criar uma duplicata.

## Instalação no ambiente de desenvolvimento

Para uma instalação nova:

```bash
./erpctl install development 10.20.0.74
```

Confirme no `.env.dev`:

```dotenv
ERP_PORT=8021
DJANGO_ALLOWED_HOSTS=10.20.0.74,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://10.20.0.74:8021,http://localhost:8021
```

Para atualizar um ambiente de desenvolvimento já instalado:

```bash
./erpctl update development projeto-erp-v1.3.0-dev.2.tar.gz SHA256_DO_PACOTE
```

O `erpctl` preserva `.env.dev`, banco e mídias; faz backup antes de aplicar o código e executa
as migrations automaticamente na inicialização do container.

## Roteiro de homologação

1. Crie duas seções no Admin, por exemplo `Backbone` e `Clientes`.
2. Crie duas VRFs e cadastre o mesmo prefixo em ambas, confirmando o isolamento.
3. Cadastre um bloco IPv4 contêiner `/20` e gere dois filhos `/24`.
4. Cadastre um IPv6 `/32` contêiner e solicite os próximos dois `/48`.
5. Em uma rede IPv4 pequena, registre IPs e confira o mapa visual.
6. Pesquise pelo hostname, IP, VLAN e nome do equipamento.
7. Entre como cliente e confirme que somente os recursos da própria empresa aparecem.
8. Tente acessar manualmente `/ipam/` como cliente e confirme a resposta `403`.

## Próximas etapas sugeridas

- importação e exportação CSV/XLSX;
- reservas por faixa e pools DHCP;
- API REST com tokens e permissões;
- varredura opcional por agente, ICMP e DNS reverso;
- solicitações e aprovação de IP;
- campos personalizados e tags;
- relatórios de utilização e alertas de capacidade;
- integração do IPAM com os planos e relatórios CGNAT.
