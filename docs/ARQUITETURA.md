# Arquitetura da versão de homologação

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `gestao` | clientes, perfil financeiro, contratos e lançamentos |
| `infraestrutura` | equipamentos, VLANs, sub-redes e endereços IP |
| `helpdesk` | chamados, cronômetro e apontamentos de horas |
| `portal` | login único, vínculo usuário-cliente e área do cliente |
| `cgnat` | plano, alocação determinística, scripts e relatório PDF |
| `pagamentos` | cobrança Pix, simulador e histórico de webhooks |
| `core` | configuração, rotas globais e healthcheck |

## Limites de segurança

- scripts CGNAT são baixados apenas por usuários administrativos;
- relatórios CGNAT, cobranças Pix e contratos são filtrados pelo cliente associado ao usuário;
- o webhook do simulador exige token comparado em tempo constante;
- IDs públicos de CGNAT e Pix usam UUID;
- confirmações Pix usam bloqueio transacional e `event_id` único;
- vínculos entre objetos de clientes diferentes são validados antes da gravação;
- exclusões destrutivas de entidades centrais foram trocadas por proteção referencial;
- uploads de contratos são limitados e têm assinatura PDF verificada.

## Evolução para um PSP Pix real

A interface externa deve ficar na camada `pagamentos/services`. A próxima implementação precisa incluir:

1. adaptador do PSP e credenciais somente por variáveis/secret store;
2. criação de cobrança e armazenamento do identificador do provedor;
3. verificação criptográfica do webhook conforme o PSP;
4. consulta de conciliação para recuperar eventos perdidos;
5. política de expiração, estorno e cancelamento;
6. logs de auditoria sem expor segredos ou payloads sensíveis.

O modelo atual já separa `txid`, identificador do provedor, status, horário de pagamento e eventos recebidos. Isso permite trocar o simulador sem reescrever o portal.

## Escala do gerador CGNAT

Cada plano aceita até 4.096 assinantes por geração para limitar tempo de processamento, tamanho dos scripts e PDFs. Para volumes maiores, prefira particionar por concentrador/POP. Uma evolução futura pode mover a geração de arquivos para uma fila, mas isso não é necessário para a homologação atual.

