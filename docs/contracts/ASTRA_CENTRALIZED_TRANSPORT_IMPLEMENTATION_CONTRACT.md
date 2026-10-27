# ASTRA — Contrato complementar de transporte centralizado

```text
PROJECT_ID = projeto_cam_scanner
ACTIVITY_ID = CAM_SCANNER_ASTRA_CONTRACT_FINALIZATION_02
PARENT_ACTIVITY = CAM_SCANNER_ASTRA_CONTRACT_CLOSURE_01
CONTRACT_ID = ASTRA_CENTRALIZED_TRANSPORT_V1
DOCUMENT_STATUS = PROPOSED
CONTRACT_STATUS = READY_FOR_FINAL_NORMATIVE_APPROVAL
TECHNICAL_DIRECTION_STATUS = APPROVED_BY_USER_CARD_FINALIZATION_02
NORMATIVE_DELTA_APPROVAL = PENDING
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
OPERATIONAL_HOMOLOGATION = NOT_AUTHORIZED
HTTP_REAL_TARGET_AUTHORIZATION = NOT_GRANTED
EXECUTION_MODE = DIRECT
MODEL_REQUESTED = ASTRA
MODEL_RUNTIME_ATTESTATION = UNAVAILABLE; nenhuma reconfiguração alegada
```

## 1. Finalidade, autoridade e fontes

Centralizar seleção de transporte por execução/lote/grupo fechado no aplicativo, aproveitando o transporte exato existente. Documento complementar necessário porque configuração, seleção pré-rede, estratégia e proveniência atravessam P0 e P1. Não reabrir fases nem editar [P1 histórico](P1_SINGLE_MINIMUM_VERTICAL_SLICE.md), [P2 histórico/D03](P2_COLLECTION_STRATEGY_EXPANSION.md), [PRE-P12 §§5–8](PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md) ou [R2](VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT_R2.md).

O Card final 02 aprovou a direção técnica, não os deltas normativos finais, implementação ou uso HTTP real. [P0 V2](ASTRA_P0_REQUIRED_CORRECTIONS_IMPLEMENTATION_CONTRACT.md) e [P1 V2](ASTRA_P1_COVERAGE_IMPROVEMENTS_IMPLEMENTATION_CONTRACT.md) são propostas complementares. [P2 mídia](ASTRA_P2_MEDIA_DEFERRED_DECISION_RECORD.md) permanece DEFERRED e não foi alterado.

Escopo operacional futuro: IP, credencial própria da câmera, fabricante/modelo conhecidos quando disponíveis; contas exclusivamente de visualização são válidas, sem garantia de todos os campos. Nenhuma habilitação ONVIF/API, troca de papel/permissão, conta nova, certificado instalado na câmera, reboot, firmware ou infraestrutura CFTV. Não exigir manutenção individual de certificados para executar o perfil HTTP previamente autorizado. HTTPS que não possa ser verificado permanece indisponível nesse caminho, sem bypass.

## 2. O que existe e o que falta — evidência focal

Baseline local: branch `feature/pre-p12-unified-remediation`, HEAD `37bc8c4cc718559fc1e6f39a9b8a1145563a551e` mais delta R2 preexistente, preservado. Inspeção estática pontual desta revisão, não nova auditoria:

| Aspecto | Evidência atual | Limite |
|---|---|---|
| Transporte exato disponível | `config/models.py:TransportRule`, `cameras/transport.py:TargetTransportPolicy` validam IP/componente/scheme/porta; HTTP depende de regra explícita | Regras não são autorização deste Card para operar parque real |
| Configuração central disponível | `config/loader.py:load_settings/_load_transport_rules` carrega TOML `transport.rules`; `EffectiveConfig.transport_rules` é imutável | Apenas target exato; CIDR/wildcard não aceitos; loader não aceita os perfis novos propostos aqui |
| Entrada principal integrada | `main.py:main` carrega settings e entrega ao InventoryService/SINGLE/MULTI | Não há seletor de perfil por execução/lote/grupo ou aceite de risco por essa seleção |
| Seleção de scheme existente | `TargetTransportPolicy.endpoint` escolhe HTTP se as regras configuradas daquele target/componente são HTTP; senão HTTPS | Combinações ambíguas/ordem de regras não são política de precedência aprovada para o novo perfil |
| Auth atual | `_GuardedAdapter.send` distingue challenge suportado em tentativa autenticada; `AuthLedger.begin/observe_http` limita famílias/logins; helpers Digest atuais | Nativo MD5/MD5-sess com qop auth/ausente; ONVIF WSSE; sem expansão de mecanismo/algoritmo |
| Ordem de coleta R2 | `strategy.py:collect_report` pode dispensar preauth com hint elegível; fonte parcial Panasonic ainda é excluída por completude | Política de transporte sozinha não torna Panasonic elegível; P0/P1 fornecem o delta explícito |
| Diagnóstico do transporte | F08 recuperado: há rotulagem fixa HTTPS em fontes nativas | P0-04 e integração deste contrato devem provar scheme realmente executado |

```text
TRANSPORT_AVAILABLE_IN_CODE = YES_HTTP_EXACT_RULES
TRANSPORT_CONFIGURABLE = YES_CENTRAL_TOML_EXACT_RULES; GROUP_PROFILE_SELECTOR_NOT_IMPLEMENTED
TRANSPORT_AUTHORIZED = ONLY_EXISTING_EXPLICIT_SCOPE_IF_PROVEN; NONE_GRANTED_BY_THIS_CARD
TRANSPORT_OPERATIONALLY_VALIDATED = NOT_ESTABLISHED_FOR_VIEWER_OR_NEW_GROUP_POLICY
```

Evidência histórica fornecida no Card: Hikvision 10.143.108.79 apresentou falha de confiança TLS; em outra seleção HTTP, GET de identidade recebeu challenge Digest e 200 com 1.135 bytes usando conta administrativa. É relato antecedente, sem replay nesta atividade; prova API naquele caminho administrativo, não Viewer, autorização HTTP futura ou segurança universal. Não copiar credenciais, cabeçalhos ou payload.

## 3. Menor mudança suficiente e fronteiras futuras

Manter TransportRule, TargetTransportPolicy, CollectionContext, AuthLedger, sessões isoladas, Requests/Zeep, budgets e limites de corpo. Acrescentar somente:

1. Catálogo restrito de perfis em configuração e um seletor por execução.
2. Validação/compilação offline do perfil em regras exatas e plano imutável por linha, antes de preauth/construtor com I/O.
3. Associação separada do modo de auth já existente e da autorização documentada.
4. Metadados fechados de política/proveniência e integração nos fluxos reais, sem alterar os 14 campos de CameraResult ou colunas de XLSX.

Paths candidatos: `config/models.py`, `config/loader.py`, `main.py`, `terminal/ui.py`, `application/single_workflow.py`, `multi_workflow.py`, `inventory_service.py`, `collection_context.py`, `cameras/strategy.py`; `cameras/transport.py` apenas para consumir regras/plano e validar consistência, sem reescrita. Projeções/metadados em `domain/models.py` e `excel/writer.py` somente como especificado na §7. Um integrador por arquivo compartilhado com P0/P1; testes em arquivos de config/transporte/entrypoint/workflows/sanitização. Nenhuma alteração nesses arquivos nesta autoria.

OUT: CIDR executável, descoberta de IP/portas, DNS/hostname de entrada, mTLS/CA/pinning novos, verify=False, TOFU, bypass de certificado, auth automática Basic/Digest/WSSE, SHA-256 Digest novo, HTTP Digest ONVIF, novas contas, API/mídia/RTSP, endpoints e hardware. AUTH-EXT permanece diferido em P0.

## 4. Proposta fechada de perfil e seleção pré-I/O

**Schema futuro para aprovação, não aceito pelo loader atual.** Estender a seção `transport` com uma lista `profiles` de objetos fechados. Nenhuma configuração operacional é criada ou editada por este contrato.

| Campo do perfil proposto | Regra |
|---|---|
| id | Identificador ASCII limitado a 64, letras/dígitos/_/-; único e não sensível |
| targets | Lista explícita não vazia de IPs canônicos exatos já aceitos pela entrada; sem duplicados, CIDR, ranges, wildcard ou DNS; não ampliar suporte IPv6 da entrada |
| component | Um único vendor component já registrado e fundamentado: vendor_hikvision, vendor_axis, vendor_dahua, vendor_hanwha ou vendor_panasonic; não habilita adapter/endpoint por si só |
| protocol / port | protocol=http neste perfil de exceção; porta inteira 1–65535 explicitamente autorizada; host é sempre o próprio IP do target |
| auth_mode | NATIVE_DIGEST_EXISTING para operação já Digest das famílias Hikvision/Dahua/Hanwha/Panasonic, quando a operação e suporte forem elegíveis; vendor_axis aceita somente PUBLIC_NONE do plano público. Não há seleção por username, perfil Operator Axis ou negociação entre modos |
| authorization_ref | Identificador não sensível com o mesmo formato de id, ligado à decisão operacional externa verificável; não conter usuário, segredo, URL ou caminho |
| http_risk_accepted | booleano true só quando reproduzir aceite explícito e vigente do responsável pelo escopo; um valor TOML isolado não cria autoridade |

Targets constituem o grupo fechado: não escanear o grupo nem expandi-lo por rede. Uma execução SINGLE aplica a interseção com seu IP; MULTI aplica a interseção com as linhas válidas. A lista de credenciais continua exclusivamente na entrada própria; perfil nunca contém username/password, realm/nonce, cookies, chaves ou conta compartilhada.

Fluxo proposto:
1. Carregar e validar configuração local; receber/validar entradas conforme o contrato vigente. Não abrir cliente/construtor com I/O durante essa etapa.
2. Oferecer uma seleção por execução: HTTPS verificado padrão ou um perfil identificado da lista. Não perguntar transporte por câmera, não criar flag global allow-http nem herança por env. P1 continua responsável apenas pelo modelo. Cancelamento da seleção encerra sem rede.
3. Mostrar resumo seguro antes da execução: id/authorization_ref, quantidade de linhas correspondentes HTTP, demais HTTPS e fontes inelegíveis; sem senha/username, URLs, conteúdo bruto ou lista de credenciais. Seleção local não substitui G-TR-OPS nem autorização de câmera real.
4. Selecionado um perfil, exigir referência e aceite de risco vinculados à autorização existente; ausência/incoerência impede HTTP. Sem interseção, recusar a seleção antes da rede. A referência e o aceite são pré-condições de execução, não uma tela para conceder permissão nova de parque. Validar todos os conflitos estruturais antes de agendar qualquer linha.
5. Para cada linha válida e correspondente, compilar exatamente uma TransportRule por componente: target=IP da linha, host=None (mesmo alvo), protocol/port aprovados. Não materializar destinos fora das entradas do lote. Linhas repetidas do mesmo IP reutilizam só valores imutáveis da regra; cada linha mantém credencial/contexto/sessão/ledger próprio.
6. Conservar HTTPS verificado para os alvos/componentes não abrangidos. O perfil não autoriza HTTP para ONVIF Device/Media, snapshots, RTSP ou outro vendor, mesmo no mesmo IP. Linhas correspondentes sem fabricante elegível não usam o component como hint nem tentam famílias: registrar etapa de política SKIPPED/compatibilidade não comprovada, sem I/O nessa linha.
7. Congelar seleção, regras e plano por linha antes da primeira operação; alteração de settings depois disso não afeta a execução. Novo perfil requer nova execução deliberada, não retry automático da coleta encerrada.

**Compatibilidade com regras exatas legadas:** o TOML `transport.rules` continua válido e o código atual já o carrega. No delta proposto, regras HTTP legadas devem aparecer como opção LEGACY_EXACT na seleção pré-I/O, com escopo e aceite operacional documentados; não ativá-las silenciosamente, descartá-las ou generalizá-las. Regras HTTPS legadas preservam validação exata. Duplicatas, duas portas/schemes/hosts concorrentes para a mesma chave target/component, sobreposição entre perfil selecionado e regra legada ou id duplicado são erro sanitizado antes de rede; não “primeira regra vence”. Perfis não selecionados não concedem acesso.

Essa exigência de seleção das regras HTTP legadas é mudança prospectiva de ativação, explicitamente sujeita a G-TR-NORM; não alegar que R2 já a oferece. Host alternativo previamente autorizado em regra legada não é ampliado pelo novo perfil e continua sujeito à autoridade específica histórica e à guarda exata.

## 5. Plano de fonte, menor privilégio e D03

Transporte responde onde/como conectar; auth responde qual mecanismo já foi autorizado para aquela operação; resolução de fabricante responde qual única família pode ser utilizada. Nenhum desses eixos cria autoridade nos outros.

Para o perfil nativo HTTP: exigir fabricante conhecido elegível segundo R2/P0 e, quando necessário, perfil de modelo documentado de P1. A escolha é feita antes de qualquer rede. Iniciar pela fonte nativa elegível, sem preauth HTTPS obrigatório anterior. A dispensa para fonte parcial Panasonic é o delta G-P0-PARTIAL, não uma capacidade presumida em R2. Se a fonte não for elegível, não contornar com preauth e retorno HTTP. O resumo/preflight deve explicar a lacuna; não inferir fabricante a partir de IP, componente, modelo ou username.

Depois de dados nativos:
- Identidade essencial completa: não autenticar ONVIF por opcionais.
- Identidade incompleta, sem recusa final, mesmo contexto/budget: ONVIF HTTPS histórico só é elegível conforme D03. Não autorizar HTTP ONVIF por este perfil. Uma falha TLS nessa complementação encerra toda rede e preserva dados nativos anteriores.
- 401 Digest inicial, suportado e sem Authorization, numa operação já planejada NATIVE_DIGEST_EXISTING: challenge da mesma tentativa lógica. Replay é só da mesma operação/mecanismo/URI validada, mediado pela guarda/budget atuais. Cada troca física é contada. 401 após negociação é final, sem loop stale-nonce/relogin ou troca de algoritmo.
- Desafio não suportado: AUTH_MECHANISM_UNSUPPORTED, sem outro mecanismo e sem replay; manter a política conservadora do ledger existente, sem iniciar auth diagnóstica.
- 401 final, 403 ou negação vendor documentada: encerrar novas autenticações em todos os componentes conforme PRE-P12. Não afirmar senha errada nem mudar para Operator.
- Axis PUBLIC_NONE continua sem auth hook/cookie/credencial e não consome login. Challenge público não habilita Digest; o perfil de transporte não muda a decisão de P0-01.
- No máximo duas tentativas lógicas por câmera, uma única família vendor, secundária apenas se faltar manufacturer/model/serial e D03 permitir. Nenhuma auth apenas para firmware/MAC/imagem. Preservar contagens, limites, cancelamento e sessões por linha.

Não aumentar requests para selecionar/validar transporte, “testar porta” ou descobrir mecanismo; seleção é local. O handshake existente é contado, não request novo de discovery. A escolha do perfil não é evidência de papel Viewer; somente resposta do serviço demonstra acesso à operação com a credencial usada.

## 6. HTTPS, HTTP e falhas

HTTPS verificado é padrão. Sem perfil/regra exata autorizada, nenhuma conexão HTTP. verify=True e trust_env=False continuam fixos; sem proxy/netrc, redirects ou confiança em XAddr não validada.

Qualquer TLS_ERROR encerra toda rede do contexto. Não criar contexto para contornar, não tentar HTTP depois, não reenviar credenciais e não converter a falha em simples timeout. Até uma regra HTTP autorizada previamente para outro componente fica impedida de executar depois desse TLS_ERROR. Planejar HTTP nativo antes da primeira conexão é diferente de downgrade após erro; os testes devem provar a ordem.

HTTP com Digest não fornece confidencialidade do inventário/tráfego e permite exposição de metadados e ataques sobre o canal/desafio; Digest não equivale a TLS. O aceite operacional deve reconhecer esses riscos, a rede e o escopo exato, o responsável e a validade da decisão; não prometer proteção só por usar Digest. A referência pública aos mecanismos não autoriza seguir exemplos anyauth ou alterar política na câmera: [Axis Authentication](https://developer.axis.com/vapix/authentication/). Este contrato mantém mecanismos atuais e D03.

CA corporativa já confiável pode continuar sendo usada pelo HTTPS atual, sem novo fluxo de cadastro individual. Se for necessário desenvolver confiança/pinning/CA customizada, tratar como escopo separado, sem implementar aqui.

## 7. Rastreabilidade e interfaces de saída

Metadado interno tipado e fechado por tentativa: policy_id (HTTPS_DEFAULT/LEGACY_EXACT/id selecionado), authorization_ref quando aplicável, scheme efetivamente tentado e modo auth selecionado. Nenhum metadado guarda segredo ou URL; não adicionar campos em CameraResult. Identificador/hint contendo credencial do alvo é rejeitado na projeção sanitizada.

P0-04 rege o scheme em UI e PROTOCOLO de DIAGNOSTICOS: HTTP/HTTPS para vendor; ONVIF/HTTP ou ONVIF/HTTPS só quando comprovado, mantendo protocolo lógico ONVIF. Preservar nove colunas de DIAGNOSTICOS e os layouts INVENTARIO/RESUMO.

Para rastrear a política sem nova coluna, propor uma única tentativa local por linha com operação allowlisted `select_transport_policy`, stage CONNECT e outcome SKIPPED (nenhuma rede nessa tentativa). Sua mensagem usa template fechado com policy_id, authorization_ref sanitizados e auth_mode; metadado scheme só surge nas tentativas de rede reais. SKIPPED da etapa local não significa alvo consultado ou inventário bem sucedido. Acrescentar somente esse literal à allowlist e os tipos/validações indispensáveis, sob G-P0-META/G-TR-NORM. CollectionReport continua canônico; usuário vê no SINGLE o mesmo identificador seguro e no MULTI a linha de diagnóstico.

Não persistir arquivo auxiliar com regras/credenciais. Auditoria futura mínima contém referência da decisão operacional, hash do perfil não sensível/inputs sem credenciais, id da linha e scheme real; nunca hash de senha, entrada XLSX original, cabeçalhos, nonce, corpo ou exceção bruta.

## 8. Matriz de dependências e gate conjunto Panasonic

| Unidade | Predecessor obrigatório | Aceite que pode ocorrer isoladamente | Entrega que exige integração |
|---|---|---|---|
| P0-01 Axis | G-P0-AXIS e ledger público/ACL | Fixture pública, operações/versão/limites e ausência de credencial | P0-04/TRANSPORT prova que HTTP não habilita auth Axis |
| P0-02 partial | G-P0-PARTIAL e interface/catálogo documentado | Parser/merge/ledger/skip/cancelamento em fluxo canônico com perfil interno de fixture | Entrada operacional por modelo conhecido depende de P1-01; nenhum PASS físico |
| P0-03/04/05 | Normativos respectivos e baseline | ACL, scheme/saídas, preservação | Regressão real SINGLE/MULTI combinada |
| P1-01 ModelHint | Interface P0-02 aceita; gates N-P1-INPUT/REPORT | Leitor/tipo/encaminhamento/modelo declarado | G-PN-JOINT; sem ciclo P0 depender de sua própria entrada futura |
| P1-02/03 | Ledger/P0-04 e fontes seguras | Diagnóstico/mapping sem I/O extra | Integração com plano selecionado e parciais |
| TRANSPORT | G-TR-NORM, interface P0-04 e plano parcial estável | Parser/perfil/seletor/compilador offline | Plano antes de preauth, D03, P0/P1, saídas SINGLE/MULTI |
| HTTP real Viewer | G-TR-OPS e autorização própria de homologação READ_ONLY | Nenhum aceite físico por fixture | Resultado por modelo/firmware/operação/conta/escopo realmente autorizados |

**G-PN-JOINT, offline:** provar o percurso CLI/XLSX → ModelHint → perfil documentado P0 → contexto/transporte/adapters reais em fixture → merge → UI/XLSX. Variantes obrigatórias: modelo exato de referência; modelo ausente/desconhecido/legado; firmware desconhecido e versão observada diferente da referência (não inventar faixa); 200 parcial sem manufacturer; identidade completa só por observação válida; 404 de operação; challenge suportado→200; 401 final; 403; TLS na complementação; deadline/cancelamento; duas linhas do mesmo IP com contas distintas.

Catálogo de suporte deve guardar modelo/família exatos, operação, referência/revisão/página e versões expressamente documentadas ou UNKNOWN. WV-S2531L é referência de exemplo do [manual i-PRO §9.1, p.204](https://i-pro.com/products_and_solutions/en/media/document/35381); não é lista universal de modelos/firmwares nem homologação física. API disponível e conta autorizada são fatos separados; 404 não significa Viewer negado e 403 não prova modelo incompatível. Sem prova documental suficiente, fonte SKIPPED; não consultar outra CGI para descobrir compatibilidade.

PASS desse gate = integração offline demonstrada; OPERATIONALLY_VALIDATED continua NOT_VERIFIED até autorização e evidência física futuras. Modelo/serial/firmware válidos são preservados sem criar fabricante a partir de declaração.

## 9. Matriz AC → testes → evidência futura

Todos PREVISTOS/NOT_RUN nesta atividade. Cada evidência futura deve identificar baseline/delta, AC, função/comando real, resultado e contagens/asserções sanitizadas. IDs T-TR são casos a criar ou adaptar; não funções já existentes.

| AC único | Resultado verificável | Teste correspondente | Evidência futura |
|---|---|---|---|
| ASTRA-TR-AC01 | Sem perfil/HTTP legado ativado, HTTPS verificado é padrão; nenhuma concessão implícita HTTP | T-TR01 config/entrypoint/transport reais | Plano e spy de requests; verify=True e zero HTTP não autorizado |
| ASTRA-TR-AC02 | Perfil aplica a grupo explícito/interseção do lote, sem enumeração; demais alvos HTTPS | T-TR02 SINGLE e MULTI com IPs de fixture | Regras exatas por linha, nenhuma conexão extra ou fora do lote |
| ASTRA-TR-AC03 | CIDR/wildcard/DNS/range/host alternativo de perfil/chaves desconhecidas/id duplicado/conflitos são rejeitados antes da rede | T-TR03 parser/compilador com casos negativos | Erros sanitizados e zero I/O/construtor com rede |
| ASTRA-TR-AC04 | Seleção, autorização vinculada e aceite de risco antecedem a primeira operação; config mutada depois não altera plano | T-TR04 CLI/workflow/main com relógio de chamadas | Ordem preflight→contexto→rede; cancelamento/ref ausente sem HTTP |
| ASTRA-TR-AC05 | TLS_ERROR em qualquer etapa encerra toda rede; nem regra HTTP prévia permite próxima operação | T-TR05 certificado inválido/preauth/complemento/snapshot existente | Falha TLS preservada, contagem pós-erro zero, nenhum novo contexto |
| ASTRA-TR-AC06 | Digest selecionado challenge→200 é uma tentativa lógica; cada troca física conta; sem novo retry de login | T-TR06 Requests/guard/ledger com ACL Viewer | logical=1, physical conforme handshake e budget, sem credencial bruta |
| ASTRA-TR-AC07 | 401 final/403/erro vendor fecha auth; Basic-only/SHA-256 não suportado não provoca troca/replay | T-TR07 variantes ACL/desafios hostis | Categorias/transições e zero auth posterior ou outra família |
| ASTRA-TR-AC08 | Perfil não implica privilégio: Viewer nega Operator; Axis público permanece sem credenciais mesmo com HTTP selecionado | T-TR08 ACL + T-P0-AX06 | Matriz papel/operação; logical_auth Axis=0 e zero getAllProperties por fallback |
| ASTRA-TR-AC09 | Sessões/credenciais/estado não atravessam linhas iguais ou targets; default/profile sem interferência | T-TR09 lote concorrente e IP duplicado | IDs de sessão/contexto separados e sentinelas cruzadas ausentes |
| ASTRA-TR-AC10 | Policy/ref/auth sanitizados aparecem no diagnóstico local; scheme corresponde só à rede real; 14 campos/nove colunas preservados | T-TR10 UI/XLSX/report reais | Enum/template permitidos, esquemas corretos e inspeção de schema/bytes |
| ASTRA-TR-AC11 | Logs/XLSX/repr/erros não contêm username/password, URL, header, body, nonce, fórmula ou secret; perfil com segredo é rejeitado | T-TR11 canários sintéticos e inputs hostis | Busca por sentinelas em todas as saídas, sem dumps de entrada |
| ASTRA-TR-AC12 | Native-first elegível não executa HTTPS preauth anterior; Panasonic depende de P0+P1; inelegível não faz I/O nessa linha | T-TR12 + T-P0-PN06/T-P1-MH08 | Sequência de operações e parciais/skip por variante; G-PN-JOINT |
| ASTRA-TR-AC13 | Secundária só por identidade essencial, sem recusa, até duas lógicas/uma família; sem descoberta de auth/porta ou request por opcional | T-TR13 matrizes D03 e contagem pré/pós | Budgets/deadline/cancel/close preservados; zero login por firmware/MAC |
| ASTRA-TR-AC14 | Regras legadas continuam válidas; HTTP exige seleção LEGACY_EXACT e autoridade; sobreposição não depende de ordem | T-TR14 compatibilidade/precedência | Fluxo antigo HTTPS e novo gate explícito HTTP; zero ativação silenciosa |
| ASTRA-TR-AC15 | Defaults, P0/P1 e transporte integrado passam regressão offline no worktree real sem reabrir mídia | T-TR15 suíte acumulada Python 3.14/Windows | Resultado novo sem falha/skip/deselection; RTSP bloqueado e baseline preservada |

## 10. Deltas normativos e decisões ainda necessárias

| Gate | Justificativa / regra afetada → nova redação | AC/teste/evidência | Dependência e decisão |
|---|---|---|---|
| G-TR-NORM | PRE-P12 regras exatas/R2 preauth → compilação local de grupo fechado, seleção pré-I/O inclusive legado HTTP, conflito fail-closed; nenhum CIDR | AC01–04/12/14; T-TR correspondentes; plano/ordem/zero I/O vedado | Aprovação final do usuário para schema/perfil/UX/plano e metadados; não editar authority histórica |
| G-P0-META + G-TR-NORM | Proveniência sem expansão de CameraResult/layout → select_transport_policy local e metadados fechados | AC10/11; T-TR10/11; saídas/schema/canários | Aceite do literal/tipos/template propostos; sem campos abertos |
| G-PN-JOINT | P0/P1 dependência → P0 infraestrutura, P1 entrada e gate conjunto offline separado da prova física | AC12 + PN05/06 + MH08 | Aprovação do critério conjunto com G-P0-PARTIAL/N-P1 |
| G-TR-IMPL | Aprovação de direção/documento ≠ execução → atividade offline futura com paths/ownership/DoD autorizados | AC01–15 e regressão | P0/P1 interfaces estáveis, baseline e autorização de implementação explícita |
| G-TR-OPS | HTTP não confidencial → autorizar conjunto exato, componentes/portas, conta existente, rede, responsável/validade e aceite explícito de riscos | Protocolo de homologação futura, resultados Viewer por modelo/firmware/operação e origem da autorização | Decisão operacional separada; não concedida por Card/fixture/perfil TOML |
| G-TR-CIDR | DEFERRED: redes/ranges não cabem na autoridade exata atual | Nenhum teste de execução CIDR neste escopo | Antes de outro contrato: aprovar redes/exclusões, limite de expansão, só IPs da entrada, snapshot exato pré-I/O, contenção IPv4/IPv6, sem descoberta, conflito/validade e aceite por responsável; auth D03 intacto |
| G-P0-AXIS-AUTH-EVIDENCE / AUTH-EXT | DEFERRED: perfil Viewer Axis autenticado ou mecanismos/algoritmos novos exigem fundamentação própria | Nenhum replay ativado neste contrato | Evidência oficial por operação/aplicabilidade e autorização normativa/execução específicas |

Conflitos com regras históricas são deltas prospectivos para aprovação, nunca alteração silenciosa da autoridade. Direção técnica aprovada; todos os gates finais/execução/operacionais acima continuam pendentes ou diferidos conforme indicado.

## 11. Sequência mínima e Definition of DONE futura

1. Aprovar deltas normativos finais P0/P1/TRANSPORT e critérios G-PN-JOINT; resolver somente decisões materiais indicadas.
2. Autorizar separadamente implementação offline; confirmar worktree R2 e hashes/delta local; não trocar por master. Fechar interfaces do plano/config/proveniência antes de editar arquivos compartilhados.
3. Implementar com testes acompanhando cada slice: P0 público Axis/ACL, infraestrutura partial e scheme; compilador/perfis TRANSPORT sem I/O; P1 ModelHint/mappings/diagnóstico; integração do plano antes de preauth.
4. Executar matrizes focais com os adapters/contextos/workflows reais em fixtures loopback; incluir HTTPS confiável e TLS inválido, ACL Viewer/Operator/Admin, SINGLE/MULTI, legado e G-PN-JOINT.
5. Rodar regressão acumulada uma vez após integração, corrigir falhas bounded e repetir somente o necessário; preservar 14 campos, layouts, D03, budgets e bloqueio RTSP. Obter revisão focal de segurança/contratos conforme governança e reconciliar continuidade em escopo autorizado.
6. Somente após gates offline e autorização própria planejar homologação READ_ONLY Viewer/HTTP por alvos exatos, riscos aceitos e interfaces já existentes. Nenhuma operação de escrita/configuração para produzir PASS.

DoD futuro: ACs com evidência nova e revisão/aceite dos deltas; integração e regressão completas; nenhum request/auth indevido; preservação de baseline; PROJECT_STATE e gate documental adequados ao escopo. Offline não comprova hardware Viewer. Build/publicação continuam separados.

Parar diante de necessidade de auth/endpoint não suportado, reset de ledger pós-falha, TLS bypass, expansão de destino/escopo, segredo em saída, dependência pendente ou baseline divergente. Reversibilidade: guardar diff por path; parar e preparar patch inverso apenas dos hunks da implementação futura sob autorização específica. Não reset/restore/clean/stash nem sobrescrever alterações alheias.

## 12. Relatório de reconciliação documental e ponto seguro

PM-01 v1.0 §12.3 exige pacote de continuidade atual, discoverability e KNOWN_STALE_STATE=NO. Os nove pins do binding foram novamente correspondidos aos bytes dos membros ZIP indicados em ACTIVE_AUTHORITY_MAP; os arquivos extraídos divergentes não foram usados como fonte de integridade e não houve migração. O trecho §12.3 foi conferido no membro PM-01 com SHA-256 pinado b0782078a57fde833577e6b46fe3cd32048dae14569cac5ba9d821aafd1b54fa. O Card §7 autoriza P0/P1/TRANSPORT e PROJECT_STATE; não concede edição dos demais documentos. Nesta atividade, lista mínima de reconciliação identificada por leitura:

| Arquivo em docs/continuity | Divergência observada | Alteração mínima futura, ainda não autorizada |
|---|---|---|
| START_HERE.md | Próximo passo ainda é publicação P2-I1; navegação anterior ao R2/Astra | Corrigir referência corrente para PROJECT_STATE e propostas P0/P1/TRANSPORT; manter P1/P2 históricos |
| handoff/LAST_HANDOFF.md | Handoff mais recente aponta P12 anterior ao build R2 e aos adendos | Acrescentar handoff corrente com baseline R2, direção aprovada, deltas pendentes e bloqueios; marcar os anteriores como históricos |
| CONTINUITY_RECORD.md | Último bloco corrente é build P12 anterior ao R2/Astra | Registrar sequência R2 → auditoria → closure01 → finalization02 e status separados; referenciar evidências existentes sem novo PASS |
| planning/ROADMAP.md | Checkpoint corrente ainda P12 | Atualizar somente ponteiro factual e pendências Astra, sem reabrir fases nem aprovar roadmap novo |
| planning/EXECUTION_PLAN.md | Checkpoint corrente P12 e recuperação anterior ainda descrita como vigente | Apontar revisão final dos deltas como próximo passo; execução offline e HTTP real explicitamente sem autorização |
| ACTIVE_AUTHORITY_MAP.md | Não localiza R2 e propostas Astra atuais | Acrescentar referências de R2 e propostas com estado correto; propostas não viram authority aprovada |

PROJECT_STATE recebe o estado novo e esta lista por referência estável; conteúdo anterior preservado como histórico. Binding/governança e NEW_AGENT_BOOTSTRAP não têm mudança necessária demonstrada neste adendo; apenas reavaliar referências na futura reconciliação. Não atualizar pins por passagem do tempo nem presumir todos os itens do gate validados.

```text
CONTRACT_FINALIZATION_STATUS = DOCUMENTS_READY_FOR_FINAL_NORMATIVE_APPROVAL
P0_CONTRACT_STATUS = READY_FOR_FINAL_NORMATIVE_APPROVAL
P1_CONTRACT_STATUS = READY_FOR_FINAL_NORMATIVE_APPROVAL
TRANSPORT_CONTRACT_STATUS = READY_FOR_FINAL_NORMATIVE_APPROVAL
P2_DECISION_STATUS = DEFERRED_UNCHANGED
AXIS_VIEWER_DECISION = ANONYMOUS_ONLY_CONSERVATIVE; AUTHENTICATED_VIEWER_PROFILE_DEFERRED
PANASONIC_DEPENDENCY_DECISION = P0_INFRASTRUCTURE_THEN_P1_INPUT_THEN_G_PN_JOINT_OFFLINE
HTTP_DIGEST_POLICY_DECISION = PRESELECTED_EXACT_GROUP_NATIVE_ONLY; NORMATIVE_AND_OPERATIONAL_GATES_SEPARATE
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
OPERATIONAL_HOMOLOGATION = NOT_AUTHORIZED
FORMAL_ACTIVITY_CLOSURE = BLOCKED_PM01_12_3_CONTINUITY_SCOPE
SAFE_RESUME_POINT = revisar deltas finais propostos; nenhum contrato executável autorizado
```

Autoria documental pronta não concede CLEARED aos findings F01–F09. Nenhuma câmera, teste funcional, instalação, build, configuração operacional ou Git write nesta atividade. Envio do relatório ao chat existente Projeto Scanner 2.0 é autorizado pelo Card §12 e deve ser confirmado pela ferramenta, com DELIVERY_STATUS factual no PROJECT_STATE.
