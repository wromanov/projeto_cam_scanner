# ASTRA — Contrato P1: melhorias de cobertura e modelo declarado

```text
PROJECT_ID = projeto_cam_scanner
ACTIVITY_ID = CAM_SCANNER_ASTRA_CONTRACT_FINALIZATION_02
CONTRACT_ID = ASTRA_P1_COVERAGE_IMPROVEMENTS_V2
PARENT_ACTIVITY = CAM_SCANNER_ASTRA_CONTRACT_CLOSURE_01
DOCUMENT_STATUS = PROPOSED
CONTRACT_STATUS = READY_FOR_FINAL_NORMATIVE_APPROVAL
TECHNICAL_DIRECTION_STATUS = APPROVED_BY_USER_CARD_FINALIZATION_02
APPROVAL_STATUS = PENDING_FINAL_NORMATIVE_DELTAS
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
REAL_CAMERA_ACCESS = NOT_AUTHORIZED
EXECUTION_MODE = DIRECT
```

P1 é prioridade deste adendo, não reabertura da fase histórica P1. O [contrato ASTRA P0](ASTRA_P0_REQUIRED_CORRECTIONS_IMPLEMENTATION_CONTRACT.md) é a fonte única de baseline, inventário F01–F09, guardrails e gates transversais. [P1 histórico](P1_SINGLE_MINIMUM_VERTICAL_SLICE.md), [P2 histórico](P2_COLLECTION_STRATEGY_EXPANSION.md), [PRE-P12](PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md) e [R2](VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT_R2.md) permanecem inalterados. A direção técnica foi aprovada no Card final 02; os deltas finais continuam para apreciação. Este documento não substitui contratos históricos nem concede execução.

## 1. Contexto e problema comprovado

F05: a entrada atual não transporta modelo conhecido; SINGLE tem fabricante opcional e MULTI reconhece FABRICANTE, sem MODELO. F06: HardwareId ONVIF, HardwareID Axis e MAC Panasonic podem estar na resposta e ser ignorados. F01/F02/F03 limitam uso viewer/partial e serão tratados pelo P0. F08 exige diagnóstico honesto por transporte; P1-02 complementa a interpretação de permissões e dados faltantes.

Referências recuperadas da auditoria original: `terminal/ui.py:36–46`, `excel/reader.py:94–123`, `application/inventory_service.py:39–71`, `cameras/onvif/adapter.py:118–153`, `manufacturers/axis.py:162`, `panasonic.py:207`, `domain/models.py:402–427,520–593`. Não foi repetida a auditoria nem executado teste funcional nesta autoria.

## 2. Objetivo e resultados esperados

Receber modelo como declaração opcional, melhorar explicação de resultados parciais/permissões e aproveitar campos já retornados. Não iniciar I/O adicional para completar campos opcionais nem promover declaração a dado observado.

| Situação | Resultado exigido |
|---|---|
| Identidade observada essencial completa e sem conflito | SUCCESS de IDENTITY_V1; opcionais podem continuar N/A. |
| Modelo declarado difere do observado; observado válido e identidade completa | Preservar modelo observado e SUCCESS de identidade; exibir divergência de declaração, não criar conflito entre duas observações. |
| Duas observações de modelo/serial/fabricante conflitantes | Preservar candidatos/proveniência; PARTIAL_SUCCESS quando útil; não resolver pela ordem ou pelo hint. |
| Leitura negada depois de dados úteis | Preservar dados e PARTIAL_SUCCESS se essenciais faltarem; fechar novas autenticações no escopo. |
| Campo ausente em 200 válido | Ausência de campo; não inventar “permissão insuficiente”. |
| Nenhum dado útil; só hint ou serviço alcançável | FAILED/limitação conforme contrato; hint nunca vira sucesso. |
| Cancelamento | CANCELLED com dados anteriores, sem etapa posterior. |

Nenhum dado obrigatório para identidade é preenchido a partir de model_hint. Uma falha apenas em campo complementar não retira SUCCESS de identidade completa; diagnóstico continua visível e auth continua fechado se houver recusa.

## 3. Escopo IN e OUT

**IN:** P1-01 MODEL_HINT, P1-02 PARTIAL_RESULTS_AND_PERMISSIONS e P1-03 AVAILABLE_FIELD_MAPPING. Input SINGLE opcional e coluna MODELO opcional na entrada MULTI; tipos internos e representação sanitizada compatível.

**OUT:** hostname de entrada/resolução DNS, modelo inferido por prefixo/OEM não documentado, novas colunas/atributos CameraResult, novos endpoints/requests para hostname/MAC/firmware, mudança de IDENTITY_V1, semântica de papel ou limites D03, novos mecanismos auth, mídia/RTSP/snapshot, build/dependências/Git/publicação. Duração de MULTI permanece finding/backlog conhecido fora deste contrato; nenhum PASS de desempenho é inferido.

## 4. Componentes candidatos e fronteiras de escrita futuras

| Responsabilidade | Paths relativos candidatos |
|---|---|
| Tipos e projeção | `src/cam_scanner/domain/models.py`: ModelHint explícito, contexto no relatório, validação/propriedades derivadas; CameraResult inalterado |
| Entrada e encaminhamento | `terminal/ui.py`, `excel/reader.py`, `application/single_workflow.py`, `multi_workflow.py`, `inventory_service.py`, `collection_context.py` |
| Seleção por suporte | `cameras/strategy.py` e perfil parcial restrito do P0; sem inferência de fabricante ou framework novo |
| Mapeamento | `cameras/onvif/adapter.py`, `manufacturers/axis.py`, `manufacturers/panasonic.py` |
| Diagnóstico/saída | `terminal/ui.py`, `excel/writer.py`, allowlists em `domain/models.py`; sem modificar schema de resultado |
| Testes | Fixtures e testes de entrada/domínio/coletores/entrypoint/SINGLE/MULTI/XLSX/sanitização existentes; novos casos com IDs da §8 |

Um único integrador controla arquivos compartilhados com P0; responsável de testes escreve testes e valida sem alterar produção de outro owner. Não reverter trabalho preexistente nem renomear arquitetura por conveniência.

## 5. Invariantes normativas

Aplicar integralmente P0 §5, P2 D03 e PRE-P12. Modelo e fabricante declarados nunca autorizam destinos, novas portas, papéis ou auth. Nenhuma operação escrita em equipamento, nem teste negativo Set. Não alterar CameraTarget de credenciais nem os 14 campos de CameraResult. Separar erro de autenticação, autorização, disponibilidade de operação, rede, dado inválido e simples ausência de campo. Transporte continua governado pelo mesmo contexto da coleta.

## 6. Fluxos esperados por subatividade

### P1-01 — MODEL_HINT

**Tipagem proposta e fechada para aprovação:**
- `ModelHint` interno, frozen, com `declared: str` e `normalized: str`; match_key é propriedade derivada de normalized.casefold(), não campo persistido. Ausência é `None`. Não usar dict/extension bag.
- `declared` preserva o texto seguro recebido. Validar antes de normalizar: somente string, até 256 code points, sem NUL/ESC/ANSI/C0/C1, surrogate, caracteres inválidos XML/XLSX, URLs ou padrões/valores de credenciais. Recusar strings que contenham username/password do target; não ecoá-las.
- `normalized = NFC(declared)`, removendo só espaços ASCII nas pontas e compactando sequências de espaços ASCII internos. Caixa e pontuação são preservadas para exibição; match_key usa casefold para comparação. Tabs e controles não viram espaços; dados inválidos não são “consertados” para gerar identidade falsa. Valor vazio/somente espaços ASCII vira None. Não remover fabricante, hífen ou sufixo do modelo observado.
- Conteúdo que possa virar fórmula é tratado como dado e protegido na saída; entrada de célula de fórmula não é avaliada pelo app. Quando identificável pelo leitor como fórmula ou tipo não textual, é hint inválido, nunca instrução.
- Input inválido opcional é **rejeitado apenas como hint**, com `INVALID_INPUT`/operação allowlisted `validate_model_hint`, sem valor bruto. Usar None e manter coleta histórica segura com IP/credenciais válidos. Não transformar uma linha útil em FAILED só por coluna opcional inválida. Comparar credenciais requer validação por alvo, não sanitização global.
- `CameraTarget` permanece ip/username/password. `ExcelInputRow` recebe `model_hint: ModelHint | None`, repr=False; tipo interno de rejeição deve ser explícito/limitado para o workflow registrar diagnóstico, nunca raw_values. `CollectionContext` carrega a referência imutável e `CollectionReport` recebe `model_hint: ModelHint | None`; mismatch é derivado da declaração e de evidências válidas, sem booleanos duplicados/estado global. Nenhuma alteração de campos de CameraResult.
- Uma assinatura keyword-only opcional `model_hint=None` percorre create_context/collect_execution/SINGLE/MULTI. Callers históricos e fakes continuam aceitos sem fornecer o novo argumento. Quando o contexto já existe, não o recriar nem sobrescrever hint/ledger/budget.

**Entrada e compatibilidade:**
- SINGLE mantém IP, username e getpass de password; fabricante opcional R2 é preservado. Adicionar pergunta “Modelo (opcional)”; vazio conserva fluxo automático. Não adicionar prompt de papel ou senha ONVIF separada. P1 não implementa seleção de transporte; a única seleção por execução proposta pertence ao contrato TRANSPORT, antes da rede e fora das perguntas de credencial/modelo.
- MULTI mantém IP/USERNAME/PASSWORD obrigatórios e FABRICANTE opcional. Acrescentar MODELO opcional, cabeçalho case-insensitive e posição livre. Coluna ausente/vazia preserva comportamento existente; extras continuam ignoradas. MODELO duplicado após normalização é cabeçalho ambíguo: erro de planilha sanitizado antes da coleta, conforme tratamento de obrigatórios duplicados; nenhuma escolha por primeira coluna.
- Antes reservado como extra, MODELO passa a ter semântica. Para proteger compatibilidade, valor inválido é ignorado com diagnóstico, sem aborto do lote. Para fórmulas, manter o modo seguro do leitor; não alterar data_only global só para executar ou calcular planilha. Célula sem valor textual comprovável não influencia roteamento.
- MODELO declarado não vira coluna MODELO da saída: essa coluna mantém modelo observado. Não alterar INVENTARIO/RESUMO/DIAGNOSTICOS nem adicionar colunas de declaração nesta versão. SINGLE pode mostrar declaração segura e aviso de divergência; MULTI usa tentativa allowlisted `compare_model_hint` sem persistir valor na aba DIAGNOSTICOS. Relatório tipado retém a declaração segura em memória.

**Seleção e conflito:**
- Fabricante conhecido e model_hint compatível podem restringir um perfil **exato e documentado** dentro da mesma família; não selecionar vendor só pelo modelo. Tabela pequena, explícita e testada; nenhum regex heurístico de prefixos. Sem correspondência, manter rota histórica conservadora.
- Para Panasonic, model_hint alimenta a interface P0-02 aceita como infraestrutura, sem dependência circular. Seed documental restrito: WV-S2531L citado pelo manual i-PRO §9.1; firmware sem faixa garantida. A entrada exata permite tentativa documentada, não afirma API/permissão/hardware homologados. Registrar separadamente modelo declarado/observado, versão observada/UNKNOWN, aplicabilidade documental, resultado da CGI e resultado de auth. Uma leitura já permitida valida somente a combinação exercitada; 404 não prova papel insuficiente e não autoriza habilitação. Fonte/página/revisão e fixtures são requisitos para ampliar tabela, sem inferência por prefixo.
- Modelo ausente/desconhecido, legado sem prova, conflito forte ou operação não fundamentada: SKIPPED nessa fonte; nenhum request de capability, outra CGI/família ou mecanismo. Quando a operação é elegível, NAME/SERIAL/VERSION úteis sobrevivem mesmo sem manufacturer; o status continua parcial até identidade observada completa. A integração operacional por entrada depende de P0+P1; G-PN-JOINT é um gate offline, não homologação física.
- Dados autenticados/estruturados observados permanecem a fonte de identidade. Mismatch com declaração não troca adapter, não repete login e não consulta outro endpoint. Aliases de modelo só quando documentados; não presumir equivalência por nome parecido. OEM sem alias comprovado permanece UNKNOWN.
- Conflito entre observações fortes segue P2. Valor do hint nunca é EvidenceRecord model/manufacturer; não conta na coverage.

### P1-02 — PARTIAL_RESULTS AND PERMISSIONS

| Observação | Categoria mantida/uso | Diagnóstico humano esperado |
|---|---|---|
| Campo omitido/vazio em resposta válida | coverage incompleta; não inventar categoria de permissão | “Campo não informado por esta operação.” |
| 401 inicial de challenge suportado em tentativa previamente autorizada para aquele mecanismo; exclui Axis público | Negociação; mesma tentativa lógica | “Negociação de autenticação”, sem declarar falha prematura |
| 401 final | AUTH_REJECTED | “Autenticação recusada neste serviço”; não afirmar senha errada |
| HTTP 403 ou erro vendor documentado equivalente | AUTHORIZATION_DENIED; fechar ledger | “Operação não permitida à conta/escopo atual”; sem sugerir elevar papel |
| 404/405/operação documentadamente ausente | ENDPOINT_UNSUPPORTED | “Operação indisponível nesta interface/versão” |
| Erro SOAP NotAuthorized | Causa pode ser ambígua; SOAP_FAULT seguro e bloqueio conforme ledger | “Serviço negou acesso; causa específica não comprovada” |
| Timeout/recusa de conexão | Categoria de rede existente | “Falha de comunicação”; não diagnosticar permissão |
| TLS_ERROR | Falha de validação TLS, rede encerrada | “Falha TLS; coleta de rede encerrada” |
| 200 com erro/shape inválido/campo hostil | Erro vendor documentado ou INVALID_RESPONSE | “Resposta sem dados válidos para este campo/operação” |

Preservar cada evidência validada antes de erro posterior e cada tentativa em ordem. Preauth alcançável não prova autenticação. Após recusa final, nenhuma autenticação adicional vendor/ONVIF/snapshot/RTSP e nenhum novo contexto para “tentar de novo”. Leitura negada não prova que todos os campos ausentes sejam restritos: registrar negação da operação e ausência separadamente.

Mostrar status de identidade, campos observados/ausentes e operação/categoria responsável, em português claro. SUCCESS não significa 14 campos/imagem completos. Explicação deve apontar limitação do app conhecida (ex.: campo ainda não mapeado), restrição explícita do serviço ou causa NOT_VERIFIED, sem inventar diagnóstico do firmware. Manter mapeamento público agregado ErrorCode e causas finas nos diagnósticos; não criar enum aberto de strings.

### P1-03 — AVAILABLE_FIELD_MAPPING

| Fonte/resposta existente | Mapping proposto | Validação / exclusões |
|---|---|---|
| ONVIF GetDeviceInformation.HardwareId | hardware_id | String válida/limitada, sem credencial; nenhuma consulta nova |
| Axis propertyList.HardwareID do método selecionado | hardware_id | Somente se presente/permitido naquele método; não executar Operator para obter o opcional |
| Panasonic getinfo MAC | mac | Seis octetos de 48 bits; aceitar 12 hex ou seis pares separados consistentemente por ':' ou '-'; normalizar para maiúsculas com ':'; tipo/shape inválido é rejeitado |
| Campos já mapeados manufacturer/model/serial/firmware | Preservar mappings existentes válidos | Não sobrescrever por vazio nem trocar prioridade do modelo Axis silenciosamente |
| deviceName / Panasonic NAME / Dahua hardwareVersion | Nenhum novo hostname/hardware_id | NAME permanece modelo documentado; hardwareVersion não é HardwareId |
| Chaves desconhecidas, tokens, credenciais, WebURL, dumps de config | Ignorar | Sem extensão dinâmica ou persistência de conteúdo bruto |

Campos opcionais inválidos são descartados com diagnóstico sanitizado, preservando identidade válida; essenciais inválidos deixam coverage incompleta. HardwareId string “0” não é convertido em número; preservar significado documental. Ausente continua None/N/A, sem derivar MAC de serial/OUI ou fabricante do modelo. Reviewed fields que exigirem semântica ou fonte nova tornam-se pendência explícita, não mapping improvisado. Contagem física de requests antes/depois deve ser idêntica para a mesma variante de plano de P0.

## 7. Interfaces e alterações contratuais dependentes de aprovação

Propostas N-P1-INPUT (modelo opcional em CLI/XLSX e tipo fechado), N-P1-REPORT (ModelHint no relatório/contexto, operações de validação/comparação allowlisted) e N-P1-MAP (três mappings sem I/O extra) devem ser aprovadas prospectivamente. Compatibilidade do P1 histórico/14 campos e do layout de saída é preservada. A evidência de declaração não altera resolução de fabricante existente nem IDENTITY_V1.

R2 descreve entrada fabricante e uma seleção por cobertura completa; o refinamento parcial depende da aprovação P0. PRE-P12/D03 não mudam: nenhum fallback adicional após auth/TLS. Nenhum valor de model_hint amplia transporte, papel ou serviço.

## 8. Matriz AC → teste → evidência futura

Todos os casos são PREVISTOS/NOT_RUN nesta autoria. T-* identifica caso de teste a criar/reutilizar; cada registro futuro inclui baseline, ID da AC, função/comando real, resultado e asserções sanitizadas, nunca body/credencial bruto.

| AC único | Resultado verificável | Teste / método | Evidência futura |
|---|---|---|---|
| ASTRA-P1-01-AC01 | SINGLE antigo, blank e fabricante opcional mantêm fluxo; modelo válido é encaminhado sem alterar CameraTarget | T-P1-MH01 UI/workflow/contexto reais | Inputs/assinaturas, mesmo contexto e 14 campos |
| ASTRA-P1-01-AC02 | Coluna MODELO ausente/vazia/livre/case-insensitive funciona; duplicate falha antes de rede | T-P1-MH02 leitor XLSX | Linhas equivalentes e zero rede no cabeçalho ambíguo |
| ASTRA-P1-01-AC03 | Normalização NFC/espaços e limite 256 são determinísticos; controles/URL/tipo/credencial não viram hint | T-P1-MH03 parametrizado | Valores válidos preservados; inválido apenas warning, sem eco bruto |
| ASTRA-P1-01-AC04 | Hint não preenche coverage/modelo observado e não determina vendor por prefixo | T-P1-MH04 estratégia/projeção | UNKNOWN/rota histórica, sem EvidenceRecord do hint |
| ASTRA-P1-01-AC05 | Mismatch declarado/observado conserva observado e não aumenta requests/auth | T-P1-MH05 duas ordens e SINGLE/MULTI | Aviso seguro e contagens iguais; identidade correta |
| ASTRA-P1-01-AC06 | Modelo Panasonic com perfil exato documentado alcança infraestrutura P0; desconhecido/ausente/legado não força CGI | T-P1-MH06 entrypoint até adapter real/fixture | Uma leitura lógica elegível (handshake físico contado) ou SKIPPED; sem identidade fabricada |
| ASTRA-P1-01-AC07 | Planilhas anteriores com extras e MODELO inválido mantêm linhas válidas | T-P1-MH07 regressão leitor/writer | Inventário observado, sem fórmula executada ou layout novo |
| ASTRA-P1-02-AC01 | Campo ausente, 401 challenge/final, 403, 404, rede, TLS e SOAP têm diagnóstico distinto | T-P1-PR01 tabela §6 | Categoria/etapa/texto controlado por cenário |
| ASTRA-P1-02-AC02 | Evidências úteis sobrevivem a negação e timeout posteriores | T-P1-PR02 integração/merge | Campos/proveniência anteriores intactos e status contratual |
| ASTRA-P1-02-AC03 | Recusa final fecha todas as autenticações futuras, inclusive imagem | T-P1-PR03 ledger/entrypoint | Zero auth posterior, sem contexto reiniciado |
| ASTRA-P1-02-AC04 | Status não trata hint/discovery como completude; conflito/cancelamento não é ocultado | T-P1-PR04 domínio/UI/XLSX | Quatro status e valores None/N/A verificáveis |
| ASTRA-P1-02-AC05 | SINGLE e MULTI mostram limitações sem URL, header, body, credencial ou fórmula | T-P1-PR05 canários e sanitização | Saídas/bytes de workbook sem sentinelas e fórmulas ativas |
| ASTRA-P1-03-AC01 | HardwareId ONVIF válido é preservado; ausente/inválido não inventado | T-P1-FM01 collector real + fixture de resposta | Campo correto e mesma contagem de requests |
| ASTRA-P1-03-AC02 | HardwareID Axis depende só da resposta pública/elevada já selecionada | T-P1-FM02 variantes P0 | Valor válido/None, zero auth/requests só por opcional |
| ASTRA-P1-03-AC03 | MAC Panasonic válido normaliza; ausente/inválido fica None/N/A | T-P1-FM03 parser/cadeia parcial | Formatos válidos, rejeição segura e identidade preservada |
| ASTRA-P1-03-AC04 | deviceName/hardwareVersion/chaves desconhecidas não viram hostname/HardwareId | T-P1-FM04 negativo | Sem campo fabricado e sem expansão de schema |
| ASTRA-P1-03-AC05 | Vazio, conflito e segredo em qualquer novo campo não apagam dado anterior | T-P1-FM05 merge nos dois sentidos | Proveniência determinística e valores hostis ausentes |
| ASTRA-P1-01-AC08 | Entrada SINGLE/MULTI → ModelHint → perfil P0 → CGI → merge/saída distingue suporte, disponibilidade e conta nas variantes conjuntas | T-P1-MH08 + T-P0-PN06 + ASTRA-TR-AC12 | Matriz modelo/versão/HTTP status/categoria/contagens; P0 isolado não rotulado homologado |
| ASTRA-P1-G-AC01 | Novos mappings/hints não alteram transporte/ledger/RTSP, 14 campos e fluxo integrado | T-P1-REG01 suíte acumulada pós-P0 | Regressão nova Python 3.14/Windows sem falhas/skips/deselection |

## 9. Testes positivos, negativos e regressão

Além da matriz, preservar testes R2 de hint fabricante/mismatch/ordem/diagnóstico, ACL por papel P0 e transporte real com Requests/Zeep em loopback. Payload 200 não substitui autorização; caso Viewer/Operator/Admin tem comportamento controlado por ACL. Nenhum teste tenta Set em hardware.

Usar as mesmas funções de projeção e workflows produtivos, com transporte fixture restrito a loopback quando futuramente autorizado. Coletores nativos e parsing reais devem participar dos testes de entrypoint; mocks de adapter que só devolvem fabricante não bastam como prova integrada. Manter testes de partial/failure/cancel, saneamento de planilha, concorrência por câmera e fechamento de recursos. Não atribuir aos testes offline compatibilidade física.

## 10. Segurança e proteção de credenciais

Hint é entrada não confiável e pode conter credencial por engano. Validação por alvo antes de armazenar/exibir; repr=False e sem dado bruto em erro. Nenhum hint vira URL, nome de arquivo, query ou conteúdo de código. Sanitizar XML/XLSX e proteger fórmulas depois da validação de texto. Sessões e dados de cada linha isolados, mesmo quando IP/modelo se repetirem. Credencial não é usada para descobrir papel por tentativa de operação elevada.

## 11. Dependências, ordem e integração

| Unidade | Gate de P0 requerido antes de implementar | Ordem |
|---|---|---|
| P1-01 MODEL_HINT | Deltas normativos e execução próprios; interface P0-02 aceita como infraestrutura, P0-04 e ACL estáveis; sem exigir prova por entrada P1 antes de P1 | Tipos/validação → entrada/encaminhamento → seleção restrita → diagnóstico; integração contínua |
| P1-02 parciais/permissões | P0-03 e P0-04 aceitos; ledger e categorias estáveis | Matriz de falhas → projeção/merge → apresentação SINGLE/MULTI |
| P1-03 fields | P0-01/P0-02 integrados e seguros | ONVIF → Axis → Panasonic; nenhum request adicional |

Gate final P1 depende do P0 aceito no seu escopo de infraestrutura e da regressão combinada. Gate G-PN-JOINT exige os testes de entrada P0+P1, sem retroativamente exigir P1 para o aceite isolado de P0. O contrato TRANSPORT é dependência apenas dos cenários de perfil centralizado; P1 por si só funciona em HTTPS padrão/regras exatas aprovadas. Não declarar subparte isolada integrada nem iniciar por uma interface ainda em disputa. Implementação de modelo pode ser preparada após contratos estáveis, mas não iniciar atividades dependentes com predecessor/gate requerido pendente.

DIRECT é recomendado pelo compartilhamento de tipos, reader, workflows e estratégia. Se multiagente futuro for autorizado e trouxer ganho verificável, só atribuir testes ou mappings em arquivos exclusivos após fechar interfaces; mesmo arquivo não recebe escritores concorrentes.

## 12. Gates, evidências e condições de parada

G-P1-0: aprovar deltas N-P1 e conceder execução offline específica. G-P1-1: confirmar baseline pós-P0 e interfaces. G-P1-2: módulo/integração/fluxo acumulado. G-P1-3: ACs e regressão conjunta P0/P1, incluindo G-PN-JOINT. G-P1-4: revisão de segurança de inputs/saídas/proveniência e estado documental conforme governança. Homologação operacional e publicação não são concedidas.

Parar se for necessário inventar alias de vendor/modelo, aumentar requests/auth para opcional, mudar schema público, ampliar endpoint/transporte, esconder informação negada/erro, tocar câmera ou superar escopo de escrita. Baseline divergente ou falha de teste/preservação bloqueia o escopo afetado. Não “corrigir” fixtures para ocultar falha produtiva.

## 13. Riscos, limitações e decisões pendentes

Modelo declarado pode estar incorreto; continua como declaração. Nome idêntico não garante firmware/permissões. Campo retornado pode conter valor impróprio; ausência não prova restrição. Compatibilidade viewer real e mídias continuam NOT_VERIFIED/DEFERRED. Novos inputs são mudança contratual prospectiva, mesmo compatíveis por defaults.

Decisões materiais para aprovação têm proposta definida: ModelHint fechado/256/NFC; hint inválido descartado com diagnóstico sem matar a linha; duplicate MODELO rejeitado antes de rede; saída sem coluna de modelo declarado; três mappings sem I/O. Não há necessidade de escolher biblioteca/algoritmo de auth neste contrato; AUTH-EXT permanece separado. Hostname de entrada e novas leituras de rede continuam fora do escopo.

## 14. Rollback e reversibilidade

Nenhuma migração, armazenamento ou mutação de câmera. Manter inputs antigos operantes com model_hint=None e dados opcionais ausentes. Guardar diff e baseline da implementação futura; se necessário, parar e preparar patch inverso apenas dos hunks do executor, submetido a autorização específica. Nunca usar reset/restore/clean/stash ou apagar planilha com credenciais para reverter. Remover suporte a modelo não pode alterar o valor observado em relatórios existentes.

## 15. Definition of DONE e status

Futura implementação P1 só DONE após P0 requerido aceito, G-P1-0…4, todas as ACs com evidência nova, regressão integrada sem falhas/skips/deselection, 14 campos e layouts de saída preservados, nenhum I/O extra por opcionais e estado de continuidade reconciliado no escopo autorizado.

Nesta autoria: todos os testes são propostos/NOT_RUN; CONTRACT_STATUS=READY_FOR_FINAL_NORMATIVE_APPROVAL; CONTRACT_AUTHORING_COMPLETE não equivale a IMPLEMENTATION_APPROVAL; IMPLEMENTATION_AUTHORIZATION=NOT_GRANTED. A matriz global de findings está em ASTRA P0 §14; o [registro P2](ASTRA_P2_MEDIA_DEFERRED_DECISION_RECORD.md) mantém mídia diferida. Próxima ação é aprovação final dos deltas normativos já orientados pelo usuário, sem execução automática.

## 16. Adendo final 02 — dependência Panasonic e reconciliação

Revisão anterior V1 SHA-256 `5b60230e5a7ceba9be19103bf9c2f4f172a0257687b0a3a08a8f9fa9bda1aced`; proposta refinada, sem reabrir fases históricas. Todos os 18 IDs originais foram conservados; acrescentado ASTRA-P1-01-AC08.

| Delta / justificativa | Regra afetada → nova redação vigente | AC / teste | Evidência futura | Dependência | Gate de aprovação |
|---|---|---|---|---|---|
| B2: provar percurso de entrada sem bloquear P0 por P1 ausente | §6/11/15 → P0 infraestrutura → P1 entrada → G-PN-JOINT offline; sem rótulo de homologação | MH06/MH08; T-P1-MH06/08 e T-P0-PN06 | Mesmos adapters/contexto/workflows; requests e parciais por variante | Interface P0-02 estável; P0-03/04 | N-P1-INPUT/REPORT; G-PN-JOINT |
| B3: separar compatibilidade de permissão | §6 → catálogo documental exato; versão desconhecida explícita; 200/401 final/403/404 distintos | MH04/06/08 e PR01–03 | Manufacturer ausente preservado; nenhuma CGI não fundamentada | Catálogo P0 e D03 | G-P0-PARTIAL + G-P1-3 |
| C2: não duplicar prompts/transporte dentro do modelo | §5/6/11 → P1 encaminha hint; TRANSPORT escolhe plano antes de rede | G-AC01/MH08; T-P1-REG01/MH08 e ASTRA-TR-AC12 | Mesmo ledger/config por linha; zero mudança de CameraResult/layout | P0-04; TRANSPORT só para perfil centralizado | G-TR-NORM/IMPL e G-P1-0 |
| S2: direção aprovada e deltas finais separados | Cabeçalho/§15 → READY_FOR_FINAL_NORMATIVE_APPROVAL, execução NOT_GRANTED | Revisão documental | Coerência entre contratos e PROJECT_STATE | Card final 02 | Aprovação final do usuário |

Matriz de dependências, critérios de integração, transporte e reconciliação mínima: [TRANSPORT §§8–12](ASTRA_CENTRALIZED_TRANSPORT_IMPLEMENTATION_CONTRACT.md). P2 permanece diferido, sem reescrever requisitos. Nenhuma permissão da câmera é alterada para satisfazer testes ou o catálogo.
