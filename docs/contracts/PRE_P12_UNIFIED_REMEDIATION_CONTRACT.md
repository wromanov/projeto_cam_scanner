# Contrato unificado de remediação pré-P12

| Campo | Valor |
|---|---|
| Projeto | `projeto_cam_scanner` |
| Atividade | `PRE_P12_UNIFIED_REMEDIATION_CONTRACT` |
| Pacote | `PRE_P12_UNIFIED_REMEDIATION` |
| Status deste documento | `APPROVED_WITH_ADJUSTMENTS` |
| Aprovação do usuário | `GRANTED` |
| Implementação | `GRANTED_FOR_OFFLINE_REMEDIATION_ONLY` |
| Prontidão P12 | `BLOCKED` por PREP12-01, PREP12-02 e PREP12-03 |

Este documento registra o contrato aprovado com ajustes para os 14 findings da auditoria. Ele não os reabre nem altera sua classificação histórica. A autorização concedida cobre somente a remediação offline definida neste contrato; não autoriza build P12, acesso a câmeras, publicação ou fechamento de fase.

## 1. Identificação e autoridade contratual

| Campo | Valor |
|---|---|
| Atividade | `PRE_P12_UNIFIED_REMEDIATION_CONTRACT` |
| Tipo | Consolidação de contrato arquitetural |
| Modo de remediação | Uma implementação integrada, com divisão interna de ownership |
| Agente técnico | Architect — GPT-6.1 Sol / High |
| Materialização documental | Scribe — GPT-6 Luna / Medium |
| Implementação autorizada | Somente remediação offline contida neste contrato |
| Diagnóstico adicional | Não utilizado; auditoria encerrada |
| Estado de aprovação | `APPROVED_WITH_ADJUSTMENTS`; aprovação e autorização offline concedidas |

As recomendações abaixo reproduzem o handoff técnico do Architect e as fontes primárias da auditoria. A aprovação com ajustes incorpora ao contrato o schema de transporte por alvo, o teto de 1 MiB para corpo SOAP, as faixas configuráveis estritas e `backupCount >= 1`. A implementação autorizada permanece limitada à remediação offline; as demais decisões listadas na seção 18 continuam exigindo autoridade específica.

## 2. Baseline e fontes

```text
REPOSITORY = C:\Users\walacedelgado\PycharmProjects\projeto_cam_scanner_pre_p12_audit
BRANCH = audit/pre-p12
BASELINE = b4c67f74bead61a40ab9037934f994dad7dfe701
AUDIT_RESULT = COMPLETED_WITH_FINDINGS
P12_READINESS = BLOCKED
D00_D06 = PRESERVED
D07 = DEFERRED
CAMERA_RESULT = 14_FIELDS
IDENTITY = IDENTITY_V1
P1 = CLOSED
P2 = IN_PROGRESS
```

Fontes primárias: `docs/audit/PRE_P12_ARCHITECTURE_AUDIT_REPORT.md`, `docs/audit/PRE_P12_FINDINGS_REGISTER.md`, `docs/continuity/PROJECT_STATE.md` e `docs/continuity/CONTINUITY_RECORD.md`. Os dois documentos da auditoria registram as evidências, referências, reprodução e recomendações por finding; este contrato acrescenta comportamento-alvo, dependências, escopo de ownership e aceite integrado.

Contexto de validação que permanece histórico: pytest da auditoria parcial, com 213 aprovados e 7 inconclusivos/deselecionados por ACL do diretório temporário. Os nomes desses sete testes não foram fornecidos e não são inferidos. A referência histórica distinta de 220 testes aprovados não é resultado desta auditoria. Ruff e `pip check` foram reportados como aprovados; build P12 e câmera real não foram executados.

## 3. Objetivo e escopo

Definir um contrato único, executável e verificável para remediar os 14 findings, evitando políticas paralelas de transporte, autenticação, orçamento ou dados. A remediação offline autorizada integra os fluxos SINGLE e MULTI sem fragmentar o pacote em 14 atividades ou aprovações humanas.

Inclui: transporte ONVIF/HTTP/snapshot/RTSP; estado de autenticação e ledger por coleta; budget e cancelamento cooperativo; validação de dados/XML/XLSX; configuração e dependências; preparação offline do empacotamento; cobertura do caminho real de seleção de adapters; logging e reconciliação documental.

Não inclui: build P12; homologação de câmera real; credenciais reais; novos endpoints sem fundamento; suporte universal; alteração dos contratos de domínio; ampliação dos limites D03; reabertura de D07; encerramento ou publicação de fase.

## 4. Matriz dos 14 findings

Severidades, evidência, prioridade e blocker preservam o registro original. `ACCEPTANCE_STAGE` e `EXPECTED_EFFORT` são classificação contratual proposta, não reclassificação da auditoria.

| ID | Severidade original | Evidência original | Prioridade original | Blocker para iniciar P12 | Estágio de aceite principal | Esforço proposto |
|---|---|---|---|---|---|---|
| PREP12-01 | HIGH | CONFIRMED | MUST_FIX_BEFORE_P12 | YES | PRE_P12_REMEDIATION | HIGH |
| PREP12-02 | HIGH | CONFIRMED | MUST_FIX_BEFORE_P12 | YES | PRE_P12_REMEDIATION | MEDIUM |
| PREP12-03 | HIGH | CONFIRMED | MUST_FIX_BEFORE_P12 | YES | PRE_P12_REMEDIATION | HIGH |
| PREP12-04 | MEDIUM | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | HIGH |
| PREP12-05 | MEDIUM | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | MEDIUM |
| PREP12-06 | MEDIUM | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | MEDIUM |
| PREP12-07 | MEDIUM | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | LOW |
| PREP12-08 | MEDIUM | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | HIGH |
| PREP12-09 | MEDIUM | UNVERIFIED_RISK | RECOMMENDED_BEFORE_DELIVERY | NO | P12_BUILD | HIGH |
| PREP12-10 | MEDIUM | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | HIGH |
| PREP12-11 | LOW | CONFIRMED | POST_DELIVERY_BACKLOG | NO | PRE_P12_REMEDIATION | LOW |
| PREP12-12 | LOW | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | LOW |
| PREP12-13 | MEDIUM | UNVERIFIED_RISK | RECOMMENDED_BEFORE_DELIVERY | NO | REAL_CAMERA_HOMOLOGATION | HIGH |
| PREP12-14 | MEDIUM | LIKELY | RECOMMENDED_BEFORE_DELIVERY | NO | PRE_P12_REMEDIATION | MEDIUM |

### Fichas de rastreabilidade e aceite

#### PREP12-01 — Transporte ONVIF sem governança efetiva

- `FINDING_ID`: PREP12-01; `ORIGINAL_SEVERITY`: HIGH; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório de auditoria §5–6; registro §PREP12-01; `src/cam_scanner/cameras/onvif/adapter.py:40`, `cameras/preauth.py:75`, `snapshot/onvif.py:103`, `snapshot/rtsp.py:93`, SDK `operator.py:226–227`, `client.py:138`, Zeep `transports.py:84`.
- `ROOT_CAUSE`: confiança na abstração SDK sem governar a sessão e cada requisição antes do primeiro I/O. A inspeção local encontrou SDK ONVIF 0.4.4, Zeep 4.3.3, requests 2.34.2 e lxml 6.1.3 (observações do ambiente, não pins aprovados). `ONVIFClient` não aceita Session/Transport; dispara `GetServices` ou fallback `GetCapabilities` no construtor; cria sessão com `trust_env=True` e validação TLS default desabilitada. Alterar a sessão depois é tarde.
- `AFFECTED_COMPONENTS`: fachada/adapter ONVIF, preauth, descoberta, snapshots ONVIF/RTSP e fluxos SINGLE/MULTI.
- `TARGET_BEHAVIOR`: cada operação sai apenas para IP/host/porta/scheme autorizados; HTTPS valida certificado por padrão; proxy/env/netrc não participam; nenhum redirect é seguido; sessão e recursos são isolados e fechados.
- `PROPOSED_CHANGE`: fachada ONVIF estreita Device/Media sobre Zeep e WSDL local já disponível, com transporte controlado injetado antes do primeiro I/O. Reutilizar serializers/bindings/recursos locais; sem substituição integral da biblioteca, monkeypatch global/site-packages ou fetch de WSDL/imports externos. Preservar API interna requerida pelos providers. Toda URL/XAddr é não confiável e validada antes de usar/reescrever; aceitar somente host/portas permitidos, sem userinfo, fragmento, credencial ou hostname que amplie o alvo. Desabilitar redirects 301/302/303/307/308, inclusive retransmissão Digest; limitar corpo SOAP a 1 MiB e fechar em todos os caminhos. Schema TOML aprovado para transporte por IP/componente/porta.
- `INVARIANTS`: D01–D06 preservadas; D07 continua diferida; operações somente leitura; TLS inválido => `TLS_ERROR`, sem `verify=False`, TOFU ou downgrade; não reenviar SOAP/credenciais em redirect; nenhum WSDL externo.
- `DEPENDENCIES`: PREP12-02 e 08; PREP12-03/04/05; PREP12-10; política única de transporte.
- `IMPLEMENTATION_OWNER_SCOPE`: transporte/fachada ONVIF e interfaces do limite de rede, com integrador central definindo o contrato de contexto.
- `REQUIRED_UNIT_TESTS`: scheme/host/port allowlist, TLS default, HTTP explícito restrito, XAddr divergente, URL com userinfo/fragmento, limite de corpo, close em sucesso/erro.
- `REQUIRED_INTEGRATION_TESTS`: Zeep/requests real (não apenas fakes) em SINGLE e MULTI; validação HTTPS confiável; sessão sem proxies/netrc; descoberta e chamadas SOAP autorizadas.
- `NEGATIVE_TEST_CASES`: certificado ruim não faz fallback; todos redirects 30x recusados sem reenviar credenciais; endpoint anunciado fora de alvo não recebe conexão; nenhum proxy/netrc/env credential; nenhum fetch/import externo.
- `ACCEPTANCE_CRITERIA`: A, C, D, E, F, U e T satisfeitos; transporte entra na guarda antes da chamada construtora que realiza I/O.
- `VERIFICATION_METHOD`: testes integrados offline com servidor/fakes controlados, inspeção de requests reais de Zeep e revisão de segurança independente.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: YES.
- `RESIDUAL_RISK`: deadline é cooperativo quando a biblioteca bloqueia; interoperabilidade de modelos reais segue homologação separada. Compatibilidade de certificados não é presumida.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-02 — Snapshot HTTP fixo

- `FINDING_ID`: PREP12-02; `ORIGINAL_SEVERITY`: HIGH; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §6/9; registro §PREP12-02; `snapshot/manufacturer.py:55`, `snapshot/onvif.py:105–110,132`, teste `tests/test_snapshot_pipeline.py:208`.
- `ROOT_CAUSE`: política de snapshot separada e fixa em HTTP/porta 80; `CameraTarget` não expressa autorização HTTP explícita.
- `AFFECTED_COMPONENTS`: snapshot vendor e ONVIF, URLs obtidas de ONVIF, CameraTarget/config e workflow pós-coleta.
- `TARGET_BEHAVIOR`: snapshot usa o mesmo contexto e allowlist por alvo/componente. HTTPS validado é o default; HTTP somente após autorização explícita para alvo, componente e porta exatos. `verify=True` em HTTP não representa TLS.
- `PROPOSED_CHANGE`: integrar snapshot à política unificada de transporte, sem inferir esquema/porta e sem downgrade automático. URL fornecida pelo dispositivo é validada como input não confiável. Usar o schema aprovado de transporte por alvo; HTTP somente com autorização explícita para alvo, componente e porta exatos.
- `INVARIANTS`: D04; sem HTTP implícito, sem fallback HTTP após falha HTTPS, sem expansão de alvo; imagem é complementar à identidade.
- `DEPENDENCIES`: PREP12-01, 03, 08; política de autenticação/contexto.
- `IMPLEMENTATION_OWNER_SCOPE`: snapshot HTTP/ONVIF e workflows, integrado ao owner de transporte.
- `REQUIRED_UNIT_TESTS`: escolha scheme/porta conforme regra explícita; URL anunciada permitida/negada; escopo de componente.
- `REQUIRED_INTEGRATION_TESTS`: snapshot HTTPS com certificado confiável; HTTP explicitamente permitido no alvo correto; SINGLE/MULTI compartilham contexto.
- `NEGATIVE_TEST_CASES`: HTTP sem configuração negado; HTTPS com cert inválido não faz downgrade; host/porta não autorizados e redirects recusados.
- `ACCEPTANCE_CRITERIA`: C, D, G, H, J e U satisfeitos.
- `VERIFICATION_METHOD`: integração offline do snapshot service com transporte controlado e asserts de destino efetivo.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: YES.
- `RESIDUAL_RISK`: câmeras com certificado não confiável falham até existir decisão explícita de confiança; compatibilidade real fica para homologação.
- `EXPECTED_EFFORT`: MEDIUM.

#### PREP12-03 — Operações autenticadas após recusa final

- `FINDING_ID`: PREP12-03; `ORIGINAL_SEVERITY`: HIGH; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §5–6/9–10; registro §PREP12-03; `single_workflow.py:39`, `multi_workflow.py:146`, projeção `collect_one`.
- `ROOT_CAUSE`: autorização inferida de status agregado (`status != FAILED`), estado local por subsistema e perda do ledger de tentativas no MULTI.
- `AFFECTED_COMPONENTS`: preauth, coleta ONVIF/vendor, SnapshotService, RTSP, SINGLE/MULTI, projeção compatível `collect_one()`.
- `TARGET_BEHAVIOR`: estado de auth explícito e por câmera: `AUTH_SCOPE_UNKNOWN`, `AUTH_NEGOTIATION`, `AUTH_ACCEPTED`, `AUTH_REJECTED_FINAL`, `AUTHORIZATION_DENIED`. Um 401 anônimo pode ser challenge; desafio Digest correto não é tentativa lógica nova, embora cada troca física consuma budget. 401 após negociação encerrada é rejeição final; 403 é negação final; SOAP NotAuthorized preserva causa desconhecida e não inicia auth diagnóstica. Não alternar Digest/Basic/WSSE automaticamente.
- `PROPOSED_CHANGE`: ledger/contexto persistente durante toda a coleta e compartilhado por ONVIF, vendor, snapshot e RTSP. No máximo duas tentativas autenticadas lógicas por câmera (primária + uma secundária somente se faltar fabricante confirmado/model/serial, sem recusa/negação e dentro do budget); uma família vendor por alvo. Sessão aceita pode continuar leitura no mesmo escopo até recusa. Pós-rejeição/negação, zero operações autenticadas posteriores; manter evidência preauth e `PARTIAL_SUCCESS`. MULTI conserva ledger; projeção `collect_one()` pode manter assinatura compatível, mas não descarta controles. Não autenticar somente para firmware, hostname ou imagem.
- `INVARIANTS`: D03 sem ampliação; credenciais isoladas por linha, mesmo IP em linhas distintas não compartilha credencial/sessão nem faz fallback entre linhas; resultado parcial não autoriza auth; nenhuma mutação/bruteforce.
- `DEPENDENCIES`: PREP12-01, 04, 05 e fluxos snapshot; interfaces/contexto central.
- `IMPLEMENTATION_OWNER_SCOPE`: integrador central/contexto, strategy e workflows; integração com transporte e providers.
- `REQUIRED_UNIT_TESTS`: transições de estado; challenge Digest versus 401 final; 403; SOAP NotAuthorized desconhecido; contador lógico/físico.
- `REQUIRED_INTEGRATION_TESTS`: SINGLE/MULTI com preauth válido e recusa final; comprovar ausência de qualquer operação posterior autenticada; preservação de evidência parcial e ordem concorrente.
- `NEGATIVE_TEST_CASES`: sem snapshot/RTSP/vendor/ONVIF após recusa; status parcial não libera auth; contexto não pode ser recriado para zerar trava; linhas duplicadas não compartilham segredo.
- `ACCEPTANCE_CRITERIA`: H, I, R e T satisfeitos; 01–03 liberados somente após revisão de segurança.
- `VERIFICATION_METHOD`: spies de transporte por alvo e ledger, asserts de zero requests autenticadas depois do estado terminal.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: YES.
- `RESIDUAL_RISK`: limites de autenticação RTSP/imagem além do D03 exigem decisão específica; não são inferidos pelo contrato.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-04 — Ausência de budget cumulativo

- `FINDING_ID`: PREP12-04; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §5/7/9; registro §PREP12-04; `cameras/strategy.py:47`, `preauth.py:117–118`, `hikvision.py:60,152`, `_http_utils.py`.
- `ROOT_CAUSE`: deadlines/contadores não propagados entre discovery, auth, vendor, fallback e imagem.
- `AFFECTED_COMPONENTS`: contexto de coleta, preauth/ONVIF, vendors, fallback, snapshot, RTSP e fila de concorrência.
- `TARGET_BEHAVIOR`: deadline monotônico nasce antes do preauth e nunca reinicia. Contexto transitório mantém deadline, budget, cancelamento, ledger de auth e sessões até concluir inventário/imagem. Relatório canônico conserva tentativas/evidências.
- `PROPOSED_CHANGE`: preservar limites aprovados: connect 3 s; read 7 s; ONVIF cumulativo 15 s; native cumulativo 10 s; soft deadline por câmera 45 s; snapshot HTTP 10 s; RTSP open 8 s; first frame 5 s; default de 0 retries de aplicação e máximo configurável de 1 retry elegível, backoff 1 s. Discovery e handshake consomem source budget; budget global considera inventário, fallback, snapshot, RTSP e espera de semáforo. Cada envio, challenge, retry, chunk e nova etapa checa restante; timeout = mínimo entre política, restante de source e restante global. Contar cada troca física. Não repetir capabilities nem inventar teto global numérico. Retry apenas leitura idempotente transitória elegível quando configurado; nunca auth, TLS, recusado, inválido, unsupported ou erro determinístico. Digest não é retry.
- `INVARIANTS`: sem paralelismo adicional dentro de câmera; limites aprovados não se ampliam; tempo monotônico; evidência já obtida é preservada.
- `DEPENDENCIES`: PREP12-01, 02, 03, 05 e 08; interfaces de transporte.
- `IMPLEMENTATION_OWNER_SCOPE`: integrador central/contexto e estratégia; cada adapter recebe o mesmo orçamento.
- `REQUIRED_UNIT_TESTS`: fake clock; cálculo do timeout restante; contabilização de trocas; elegibilidade de retry.
- `REQUIRED_INTEGRATION_TESTS`: cadeia preauth→vendor→fallback→snapshot/RTSP; sem request quando esgotado; inclusão de fila RTSP e handshake no consumo.
- `NEGATIVE_TEST_CASES`: deadline não reinicia por fase, retry, fallback ou recriação de cliente; erro de auth/TLS não é repetido; capabilities não são consultadas duas vezes.
- `ACCEPTANCE_CRITERIA`: J, K e R; operação bloqueada pode exceder soft deadline apenas até a lib/network retornar, sem novo envio após retorno.
- `VERIFICATION_METHOD`: relógio falso e transporte instrumentado, mais teste cooperativo de bloqueio com limites da biblioteca documentados.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: chamadas bloqueadas/DNS/TLS/decoder não podem ser interrompidas universalmente; hard timeout só onde a biblioteca oferece suporte.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-05 — Cancelamento não interrompe todas as etapas

- `FINDING_ID`: PREP12-05; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §7; registro §PREP12-05; `strategy.py:55,136–138`, `preauth.py:98,148`, workflow, `tests/test_p2_i1_collection.py:195`.
- `ROOT_CAUSE`: CANCELLED não é condição comum de parada e algumas camadas seguem para vendor, fallback ou snapshot.
- `AFFECTED_COMPONENTS`: coordinator MULTI, futures, strategy, clients, waits, captura RTSP e workflow de imagem.
- `TARGET_BEHAVIOR`: `cancel_event` verificado antes de criar cliente, entre fontes, antes de cada envio, durante fila/espera RTSP e chunks, e antes de snapshot. MULTI para novos submissions, cancela futures pendentes e sinaliza os ativos; ao retornarem, não iniciam nova etapa. Aguarda retorno seguro, fecha recursos e mantém parciais; não exporta lote incompleto.
- `PROPOSED_CHANGE`: propagar o mesmo evento pelo contexto por câmera e pela coordenação. `SOFT_DEADLINE` impede novos sends cooperativamente; `HARD_TIMEOUT` somente limita espera onde suportado. Não implementar D07 nem matar threads.
- `INVARIANTS`: ausência de operação posterior após cancelamento observado; evidência parcial preservada; nenhum recurso abandonado intencionalmente.
- `DEPENDENCIES`: PREP12-03/04; contexto comum e lifecycle das sessões.
- `IMPLEMENTATION_OWNER_SCOPE`: integrador central/workflows/main e contratos de context; owners de transporte implementam checkpoints e close.
- `REQUIRED_UNIT_TESTS`: cancelamento em cada checkpoint, antes de criar client, fila RTSP, chunks, e close em todos os resultados.
- `REQUIRED_INTEGRATION_TESTS`: cancelamento em preauth, vendor, ONVIF, fila RTSP e antes de snapshot em SINGLE/MULTI.
- `NEGATIVE_TEST_CASES`: nenhuma request, fallback, snapshot ou frame novo depois de cancel; nenhum export de lote incompleto; sem alegação de matar chamada bloqueada.
- `ACCEPTANCE_CRITERIA`: J, R e U; fluxo ativo preserva parcial, fecha recurso quando retorna.
- `VERIFICATION_METHOD`: evento controlado e contadores de envio/fase/recurso.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: operação bloqueada pode atrasar a saída; não há interrupção forçada de thread.
- `EXPECTED_EFFORT`: MEDIUM.

#### PREP12-06 — Controles e XLSX

- `FINDING_ID`: PREP12-06; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §6/10; registro §PREP12-06; `domain/models.py:111`, `excel/writer.py:85,148,182`, openpyxl `cell.py:164–165`.
- `ROOT_CAUSE`: valor aceito no domínio pode ser inválido para XML/XLSX ou terminal; serialização não isola todas as falhas por célula/linha.
- `AFFECTED_COMPONENTS`: validação de entrada/dados vendor, domínio, logs/terminal e escritor XLSX.
- `TARGET_BEHAVIOR`: rejeitar na entrada U+controls, ESC/C1/ANSI, surrogate e inválidos XML/XLSX sem reescrever para identidade falsa; preservar Unicode válido. Limitar tamanho antes de domínio; aplicar proteção de fórmula após sanitização, incluindo prefixos com espaços/controles. Defesa no terminal e writer para legado. Incompatibilidade localizada sinaliza campo/linha e preserva linhas válidas sem sucesso falso. Se dado essencial inválido, recalcular status sem alterar `IDENTITY_V1` nem inventar hostname/serial.
- `PROPOSED_CHANGE`: centralizar validação semântica e proteção de canal. Writer prepara células por célula/linha com `try/finally` para workbook/imagens/temporários; aplicar fórmula protection no momento da célula.
- `INVARIANTS`: `CameraResult` 14 campos; `EvidenceRecord`, `CollectionAttempt`, `CollectionReport` canônicos; `IDENTITY_V1`; identidade não é “limpa” em valor fabricado.
- `DEPENDENCIES`: PREP12-07, PREP12-14 e XLSX MULTI.
- `IMPLEMENTATION_OWNER_SCOPE`: domínio/entrada e XLSX writer, com owner único de validação de dados externos.
- `REQUIRED_UNIT_TESTS`: controles XML, ANSI, surrogate, Unicode válido, limite de tamanho, fórmulas com whitespace/controle prefixado.
- `REQUIRED_INTEGRATION_TESTS`: workbook misto com linha/célula inválida e linhas válidas, recursos fechados e relatório legível.
- `NEGATIVE_TEST_CASES`: payload inválido não derruba lote; fórmula não vira célula executável; nenhum valor de identidade substituto.
- `ACCEPTANCE_CRITERIA`: L, M, R e T.
- `VERIFICATION_METHOD`: testes de domínio/escritor e abrir workbook gerado com openpyxl em diretório temporário funcional.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: limite operacional para textos longos será definido por configuração/contrato e deve evitar truncamento silencioso.
- `EXPECTED_EFFORT`: MEDIUM.

#### PREP12-07 — `deviceName` interpretado como hostname

- `FINDING_ID`: PREP12-07; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §8; registro §PREP12-07; `cameras/manufacturers/hikvision.py:216`, contrato P2 §10.
- `ROOT_CAUSE`: campos com semântica distinta foram equiparados no parser.
- `AFFECTED_COMPONENTS`: parser Hikvision, EvidenceRecord/CameraResult e saída XLSX.
- `TARGET_BEHAVIOR`: `deviceName` nunca preenche hostname. Somente campo de fonte autorizada e semanticamente correta preenche hostname.
- `PROPOSED_CHANGE`: remover mapeamento `deviceName → hostname`; não adicionar endpoint neste pacote. Endpoint diferente exige fundamento e autoridade específica.
- `INVARIANTS`: não alterar `IDENTITY_V1`; não fabricar identidade; evidência monotônica/proveniência preservada.
- `DEPENDENCIES`: PREP12-06 e PREP12-14; schema canônico de evidência.
- `IMPLEMENTATION_OWNER_SCOPE`: ownership único vendor/dados/Hikvision junto de PREP12-14.
- `REQUIRED_UNIT_TESTS`: deviceName isolado deixa hostname ausente; fonte correta mantém mapeamento existente.
- `REQUIRED_INTEGRATION_TESTS`: resposta Hikvision completa mantém rótulo sem tratá-lo como hostname e não prejudica identidade.
- `NEGATIVE_TEST_CASES`: nenhuma chamada a endpoint novo; nenhum fallback de rótulo para hostname.
- `ACCEPTANCE_CRITERIA`: N e T.
- `VERIFICATION_METHOD`: parser fixture e comparação dos campos de evidência.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: hostname pode permanecer ausente quando não há fonte correta; isso é resultado honesto.
- `EXPECTED_EFFORT`: LOW.

#### PREP12-08 — Configuração não aplicada aos componentes

- `FINDING_ID`: PREP12-08; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §12; registro §PREP12-08; `config/loader.py:20,27`, `main.py:28–33`.
- `ROOT_CAUSE`: opções no scaffold foram tratadas como funcionalidade embora somente `concurrency.default_max_workers` chegue ao runtime.
- `AFFECTED_COMPONENTS`: settings schema/loader, entrypoint, context, transporte, coleta, snapshot, RTSP, logging e coordenação.
- `TARGET_BEHAVIOR`: validar schema completo; cada opção publicada chega ao componente responsável ou é rejeitada/retirada explicitamente. Arquivo opcional ausente recebe defaults seguros; arquivo explicitamente requerido ausente falha; erros sanitizados; chave desconhecida não é ignorada.
- `PROPOSED_CHANGE`: suportar e encaminhar as configurações efetivas indicadas nesta ficha; corrigir configs obsoletas falhando claramente. Faixas estritas aprovadas: connect `0<x<=3` (default 3), request `0<x<=7` (default 7), ONVIF `0<x<=15`, manufacturer `0<x<=10`, soft camera `0<x<=45`, retries inteiro de 0 a 1 (default 0; máximo configurável 1), backoff 1 s, workers inteiro 1–32 (default 8), guardrails fixos 1/32 não editáveis, RTSP concurrency fixo 1, snapshot HTTP <=10, RTSP open <=8 e first-frame <=5; thumbnail 320×180/q75 invariável; manter temp false; remover/marcar `stale_cleanup_hours` inaplicável; log level INFO/DEBUG, retenção 1–30 dias, tamanho 1–10 MiB. Rejeitar bool como int, NaN/Inf, timeout zero, coerção e valores fora dessas faixas. Política de transporte por alvo é schema aprovado.
- `INVARIANTS`: defaults seguros; limites de resiliência não ampliados; nenhum controle aparente sem efeito.
- `DEPENDENCIES`: PREP12-01/02/04/09/10/11.
- `IMPLEMENTATION_OWNER_SCOPE`: config/build/log owner, com integrador central conectando runtime.
- `REQUIRED_UNIT_TESTS`: tabela de schema/tipo/faixa/default, chave desconhecida, arquivo requerido ausente, erro sanitizado.
- `REQUIRED_INTEGRATION_TESTS`: spy/confirmação de valores até transporte, coleta, snapshot, RTSP, workers e logger antes da rede.
- `NEGATIVE_TEST_CASES`: opção inoperante não é aceita silenciosamente; zero, bool, NaN/Inf, coerção e valores acima do teto falham antes de conexão.
- `ACCEPTANCE_CRITERIA`: P e S; defaults sem arquivo e config inválida conforme regra.
- `VERIFICATION_METHOD`: testes de loader e fluxo entrypoint com fakes que observam os parâmetros efetivos.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: configurações efetivas devem ser encaminhadas até seus consumidores; a aprovação do schema de transporte não demonstra implementação nem autoriza inferir suporte HTTP sem configuração explícita por alvo.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-09 — Risco de empacotamento não validado

- `FINDING_ID`: PREP12-09; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: UNVERIFIED_RISK; `SOURCE_REFERENCE`: relatório §11; registro §PREP12-09; `packaging/cam_scanner.spec:8`, `config/loader.py:33`, `logging/setup.py:16–18`.
- `ROOT_CAUSE`: scaffold sem convenções verificadas de recursos empacotados, imports/hooks e caminhos graváveis. A auditoria não demonstrou falha certa do executável.
- `AFFECTED_COMPONENTS`: spec PyInstaller, WSDL/local resources, Zeep/lxml, PyAV/DLLs, certs, TOML, logs/temp e destino XLSX.
- `TARGET_BEHAVIOR`: correção técnica/preparação offline na remediação; build e smoke ONEDIR pertencem a P12 separada. Caminhos do spec não dependem do CWD; inventário local de recursos/hooks antes de incluí-los; defaults embutidos somente leitura e config externa claramente definida; logs/temp em diretório gravável por usuário fora do bundle; erro controlado se não gravável; XLSX mantém destino escolhido e não sobrescreve.
- `PROPOSED_CHANGE`: preparar referências e spec com base em inventário, incluir apenas recursos demonstrados necessários. Documentar leitura de recursos e destino gravável; validar layout offline sem declarar executável validado. Não instalar dependências nem construir nesta atividade.
- `INVARIANTS`: `P12_BUILD_VALIDATION` requer executar/testar ONEDIR Windows 11 x64 sem Python; atualização de spec não fecha finding.
- `DEPENDENCIES`: PREP12-08 e PREP12-10; APIs de recursos/path da fachada ONVIF.
- `IMPLEMENTATION_OWNER_SCOPE`: config/build owner para preparação; gates P12 para validação real do executável.
- `REQUIRED_UNIT_TESTS`: resolver paths independentes de CWD, recursos empacotados/read-only, diretório de usuário gravável ou erro controlado.
- `REQUIRED_INTEGRATION_TESTS`: preparação offline registra WSDL/Zeep/lxml/PyAV/DLL/certificados/TOML/logs/temp e bibliotecas de UI/export.
- `NEGATIVE_TEST_CASES`: não alegar PASS sem executável; caminho protegido não causa tentativa de gravar no bundle; não coletar hooks indiscriminadamente.
- `ACCEPTANCE_CRITERIA`: W para preparação; P12 build deve validar recursos, DLLs, certificados, paths com espaços/acentos, pasta protegida e destino corporativo.
- `VERIFICATION_METHOD`: inspeção do spec/inventário offline no PRE-P12; smoke em máquina/ambiente P12 como gate separado.
- `ACCEPTANCE_STAGE`: P12_BUILD. `BLOCKER_TO_START_P12`: NO (historicamente assim classificado; preparação prévia não é evidência de build).
- `RESIDUAL_RISK`: finding permanece `UNVERIFIED_RISK` até executável ONEDIR testado; nenhuma falha ou sucesso de build pode ser inferido agora.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-10 — Dependências sem reprodução garantida

- `FINDING_ID`: PREP12-10; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §12; registro §PREP12-10; `pyproject.toml:11`.
- `ROOT_CAUSE`: dependências sem versões reproduzíveis e `requests` usada diretamente sem declaração direta; `httpx` declarado sem uso localizado no código auditado.
- `AFFECTED_COMPONENTS`: manifestos, runtime Python 3.14/Windows, build tooling, hooks e recursos SDK.
- `TARGET_BEHAVIOR`: inventariar imports diretos e justificar `httpx`; fixar conjunto completo de versões resolvidas, transitivas, plataforma/Python, hashes e ferramentas/hooks de build, sujeito a gate apropriado. Não usar `pip freeze` do ambiente reutilizado como lock validado.
- `PROPOSED_CHANGE`: preparar estratégia reproduzível e dependências diretas justificadas; ambiente novo somente após autorização específica. Verificar compatibilidade de Zeep/lxml/requests/PyAV/PyInstaller/hooks sem instalar nesta atividade.
- `INVARIANTS`: não adicionar dependência por conveniência; sem mudança/install de versões nesta atividade; versões observadas em venv não são pins aprovados.
- `DEPENDENCIES`: PREP12-01, 08, 09 e 11; fontes importadas pela fachada.
- `IMPLEMENTATION_OWNER_SCOPE`: config/build/dependencies owner.
- `REQUIRED_UNIT_TESTS`: validação estática de inventário/dependências diretas e documento de resolução completa.
- `REQUIRED_INTEGRATION_TESTS`: ambiente limpo autorizado, pip check, regressão integral e smoke de packaging após definição das versões.
- `NEGATIVE_TEST_CASES`: nenhum lock declarado validado a partir de `pip freeze`; não alterar/install durante contrato; não omitir ferramentas de build da reprodução.
- `ACCEPTANCE_CRITERIA`: W; ambiente reproduzível documentado, mas instalação e gates de build continuam separados.
- `VERIFICATION_METHOD`: revisão de manifests/constraints/lock e execução em ambiente novo somente em atividade autorizada.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION (estratégia e artefatos reprodutíveis); P12_BUILD para prova empacotada. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: compatibilidade transitive/Windows depende de resolução efetiva e build P12, ainda não executados.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-11 — Rotação de logs inefetiva

- `FINDING_ID`: PREP12-11; `ORIGINAL_SEVERITY`: LOW; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §7/12; registro §PREP12-11; `logging/setup.py:27`, stdlib Python 3.14.
- `ROOT_CAUSE`: `RotatingFileHandler` tem `maxBytes=10 MiB`, mas `backupCount=0`; rollover não mantém backups e reabre em append.
- `AFFECTED_COMPONENTS`: logging/setup, settings e arquivos de log do próprio produto.
- `TARGET_BEHAVIOR`: rollover e retenção efetivos, `RUN_ID` compartilhado nos segmentos, limite por segmento e política para mensagem gigante; retenção por idade entre log ativo/backups somente do prefixo próprio; não seguir symlink nem remover arquivos alheios; log anterior bloqueado não bloqueia execução; handlers substituídos são fechados; nenhum segredo.
- `PROPOSED_CHANGE`: incluir o ajuste localizado no pacote de remediação offline e configurar `backupCount >= 1`. Manter a severidade LOW e a prioridade original `POST_DELIVERY_BACKLOG`; a inclusão no pacote não altera a classificação histórica.
- `INVARIANTS`: sem telemetria externa; sem credenciais/dados sensíveis; sem exclusão fora do prefixo do produto.
- `DEPENDENCIES`: PREP12-08; política de caminhos do PREP12-09.
- `IMPLEMENTATION_OWNER_SCOPE`: config/build/log owner.
- `REQUIRED_UNIT_TESTS`: backupCount/rollover, RUN_ID em segmentos, mensagem grande, retenção e fechamento de handler.
- `REQUIRED_INTEGRATION_TESTS`: log rotativo temporário e tentativa com log anterior bloqueado, verificando continuidade da aplicação.
- `NEGATIVE_TEST_CASES`: não seguir symlink, não apagar arquivo alheio, não registrar segredo, não bloquear por arquivo anterior travado.
- `ACCEPTANCE_CRITERIA`: S; logs sem segredo e rollover/retention efetivos.
- `VERIFICATION_METHOD`: teste em temp com geração acima do limite e inspeção de prefixos/idades.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION (incluído no pacote atual; prioridade original preservada). `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: indisponibilidade do caminho de log deve resultar em comportamento controlado sem expor conteúdo sensível.
- `EXPECTED_EFFORT`: LOW.

#### PREP12-12 — Documentação de entrada inconsistente

- `FINDING_ID`: PREP12-12; `ORIGINAL_SEVERITY`: LOW; `EVIDENCE_STATUS`: CONFIRMED; `SOURCE_REFERENCE`: relatório §1/12; registro §PREP12-12; `README.md:7,9`, `docs/continuity/planning/ROADMAP.md:8–16`, `PROJECT_STATE.md`.
- `ROOT_CAUSE`: README/roadmap não foram reconciliados após integrações offline e estado central.
- `AFFECTED_COMPONENTS`: README, roadmap, execution plan, PROJECT_STATE, CONTINUITY_RECORD e entrada de continuidade pertinente.
- `TARGET_BEHAVIOR`: documentação descreve capacidades, limitações, estado e gates sem confundir implementado offline, publicado, validado em câmera real e aprovado operacionalmente.
- `PROPOSED_CHANGE`: após resultado real do pacote, reconciliar fontes vigentes sem anunciar fase encerrada. Os caminhos reais devem ser identificados na implementação documental; não presumir que `ROADMAP.md` na raiz exista.
- `INVARIANTS`: nenhuma fase `CLOSED` sem gate; não converter resultado offline em homologação ou publicação.
- `DEPENDENCIES`: conclusão do pacote e reavaliação dos demais findings; ocorre perto do final.
- `IMPLEMENTATION_OWNER_SCOPE`: docs/revisão, sob consolidação final do integrador.
- `REQUIRED_UNIT_TESTS`: não aplicável; checagem editorial de links/campos de estado.
- `REQUIRED_INTEGRATION_TESTS`: reconciliação cruzada README↔roadmap/planning↔execution plan↔PROJECT_STATE↔CONTINUITY_RECORD.
- `NEGATIVE_TEST_CASES`: nenhuma fase fechada por atualização documental; nenhuma homologação/publicação inferida.
- `ACCEPTANCE_CRITERIA`: status e capacidades coerentes entre fontes; próximo gate explícito.
- `VERIFICATION_METHOD`: revisão cruzada factual e `git diff --check` documental.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION, após correções e resultado integrado. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: fontes externas/canônicas ausentes devem permanecer registradas como limitação, sem hash ou autoridade inventados.
- `EXPECTED_EFFORT`: LOW.

#### PREP12-13 — Exercício real de adapters no caminho de entrada

- `FINDING_ID`: PREP12-13; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: UNVERIFIED_RISK; `SOURCE_REFERENCE`: relatório §8/12; registro §PREP12-13; `cameras/strategy.py:74`, `preauth.py:20,360`, `tests/test_vendor_registry_integration.py:46–49`.
- `ROOT_CAUSE`: fluxo normal inicia sem fabricante; a evidência sintética do teste injeta fabricante e não prova discovery→resolução→registry em condições representativas.
- `AFFECTED_COMPONENTS`: entrypoint, discovery/preauth, resolução de fabricante, registry, adapters, fallback e `CameraResult`.
- `TARGET_BEHAVIOR`: testes offline estruturados exercitam entrypoint→discovery→manufacturer hint/resolução→registry→adapter/fallback→CameraResult. Fixtures GetCapabilities/extensões representativas; hint P1 aprovado é suportado sem ser tratado como prova universal. Não promover substring a evidência forte; fabricante injetado isoladamente não prova fluxo operacional.
- `PROPOSED_CHANGE`: preparar fixtures por sinais estruturados e caminhos de fallback honestos; endpoint/modelos reais continuam homologação autorizada. Não declarar cobertura universal.
- `INVARIANTS`: VENDOR_FIRST_WHEN_KNOWN; um adapter escolhido, sem tentativa de credenciais de todos fabricantes; fabricante divergente não é substituído silenciosamente; `CameraResult` 14 campos.
- `DEPENDENCIES`: PREP12-01, 03, 04, 05; interfaces da strategy e registry; PREP12-06/07/14 para parsing.
- `IMPLEMENTATION_OWNER_SCOPE`: integrador central/strategy e owner único de vendors/dados; testes usam fixtures sem disputar esses arquivos.
- `REQUIRED_UNIT_TESTS`: sinais fortes/insuficientes e mapeamento de fabricante; não usar apenas injeção como prova.
- `REQUIRED_INTEGRATION_TESTS`: cada caminho de fabricante suportado via entrypoint e discovery até adapter, mais fallback ONVIF e `CameraResult`.
- `NEGATIVE_TEST_CASES`: sem substring fraca promovida, sem fallback de login, sem afirmar suporte real/universal por fixture.
- `ACCEPTANCE_CRITERIA`: Q e T; integração offline completa satisfaz o estágio offline; interoperabilidade só após câmera real autorizada.
- `VERIFICATION_METHOD`: fixtures estruturadas e spies no registry/adapters, com registro de origem do sinal.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION para fluxo offline; REAL_CAMERA_HOMOLOGATION para interoperabilidade. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: suporte efetivo por modelos/famílias permanece não verificado até homologação real.
- `EXPECTED_EFFORT`: HIGH.

#### PREP12-14 — Filtro DTD/XML dependente de encoding

- `FINDING_ID`: PREP12-14; `ORIGINAL_SEVERITY`: MEDIUM; `EVIDENCE_STATUS`: LIKELY; `SOURCE_REFERENCE`: relatório §6/8; registro §PREP12-14; `hikvision.py:211`, `tests/test_hikvision_isapi.py:241`.
- `ROOT_CAUSE`: filtro ASCII por substring antecede parser que reconhece outros encodings; UTF-16 pode intercalar NUL e contornar filtro. Bypass é provável; XXE/leitura/exaustão não foram demonstrados.
- `AFFECTED_COMPONENTS`: parser XML Hikvision, limites de resposta, biblioteca XML e evidências.
- `TARGET_BEHAVIOR`: parser existente rejeita DTD/entity antes de expansão, independentemente do encoding aceito; nenhuma entidade externa/file/network; malformed/incoherent resulta falha controlada. Aceitar UTF-8, UTF-16LE/BE suportados; manter limite Hikvision 64 KiB e limites estruturais/texto/elementos existentes. Zeep: `forbid_dtd`, `forbid_entities`, `forbid_external` true, `huge_tree` false e imports locais. Limitar corpo SOAP a 1 MiB.
- `PROPOSED_CHANGE`: usar parser com callbacks/flags de rejeição DTD antes de expansão e limites existentes; não usar regex ASCII como único controle. Preservar limites de imagem 8 MiB e 40 milhões de pixels.
- `INVARIANTS`: sem XXE, entidades externas, acesso file/rede ou expansão; XML válido suportado continua funcionando; sem ampliar import de recursos externos.
- `DEPENDENCIES`: PREP12-01 e 10; PREP12-06/07 no ownership de dados vendor.
- `IMPLEMENTATION_OWNER_SCOPE`: owner único vendors/dados/Hikvision e integração Zeep no owner de transporte.
- `REQUIRED_UNIT_TESTS`: DTD/entity UTF-8, UTF-16LE/BE; XML válido e namespace; malformed; tamanho, profundidade/texto/elementos.
- `REQUIRED_INTEGRATION_TESTS`: Hikvision ISAPI controlado; ONVIF/Zeep com parser seguro e WSDL local.
- `NEGATIVE_TEST_CASES`: documento malicioso não expande nem acessa filesystem/rede; payload excedente falha controlado; conteúdo válido não é rejeitado só por encoding permitido.
- `ACCEPTANCE_CRITERIA`: O e U; conservar o limite de 64 KiB vendor e controles de imagem.
- `VERIFICATION_METHOD`: fixtures byte-accurate nos encodings, parser real e spy que demonstra nenhuma chamada externa.
- `ACCEPTANCE_STAGE`: PRE_P12_REMEDIATION. `BLOCKER_TO_START_P12`: NO.
- `RESIDUAL_RISK`: finding permanece historicamente `LIKELY` até validação; o limite de 1 MiB é requisito aprovado, ainda sujeito à implementação e verificação.
- `EXPECTED_EFFORT`: MEDIUM.

## 5. Decisões arquiteturais

1. Permanecer no monólito existente; não introduzir framework ou persistência.
2. Uma política interna de transporte por alvo resolve scheme, IP/host/portas por protocolo, TLS, operações e limites. Regras de target são imutáveis durante uma coleta. Schema TOML por IP/componente/porta está aprovado.
3. Um contexto transitório por coleta é criado antes de preauth e vive até fechar inventário/imagem. Ele carrega deadline/budgets, cancel event, ledger de autenticação e sessões isoladas. `CollectionReport` permanece fonte canônica de tentativas e evidências.
4. `CameraResult` permanece com 14 campos; preservar `EvidenceRecord`, `CollectionAttempt`, `CollectionReport`, `IDENTITY_V1`, proveniência e merge monotônico. Status e credenciais permanecem por linha.
5. Compartilhar mecanismos de transporte/auth/budget entre SINGLE e MULTI; `collect_one()` pode manter projeção compatível sem descartar ledger de segurança.
6. Sem troca integral de SDK, monkeypatch global, persistência, endpoints especulativos, paralelismo por câmera ou reabertura de D07.

Dependências transversais confirmadas: 01+02+08; 01+03+04+05; 03 workflows; 04+05; 06+14 limites/dados; 07 mapping isolado; 08+11; 10+01; 09+10+08+11; 13 strategy+reader; 12 documentação final. PREP12-06/07/14 não têm uma única causa raiz, apesar do ownership coordenado.

## 6. Política unificada de transporte

- **Scope de destino:** scheme, host e porta são validados contra o IP aceito pelo contrato de entrada e política por protocolo/componente. IPv6 somente onde já suportado; não ampliar formato de entrada. Host anunciado não amplia alvo.
- **TLS:** HTTPS com verificação padrão. Falha de certificado => `TLS_ERROR`; sem `verify=False`, TOFU ou fallback/downgrade para HTTP.
- **HTTP:** só quando explicitamente autorizado para alvo, componente e porta exatos. HTTP implícito é negado. O schema aprovado configura a autorização por alvo.
- **Proxy e credenciais ambientais:** `trust_env=False`; sem proxy, netrc ou credenciais de ambiente. Configuração não pode ser herdada silenciosamente.
- **Sessões/cookies:** sem compartilhamento entre alvos ou linhas; credenciais próprias por linha; cookies/sessões fechados em todos os caminhos.
- **Redirecionamentos:** este pacote bloqueia 301/302/303/307/308 em todos os transportes selecionados. Não seguir nem reenviar SOAP/credenciais. Digest retransmission passa pela mesma guarda por troca física.
- **XAddr/URLs:** input não confiável; validar antes de usar/reescrever; host/porta permitidos apenas; sem userinfo, fragmento, credencial ou hostname que amplie o alvo.
- **ONVIF:** fachada estreita Device/Media com Zeep e recursos WSDL locais; transporte injetado antes do primeiro I/O do construtor. Não buscar imports externos. Operações READ_ONLY permitidas: preauth `GetCapabilities` (e `GetSystemDateAndTime` apenas se diagnóstico necessário), sem discovery equivalente repetido; inventário `GetDeviceInformation`; mídia `GetProfiles`, `GetSnapshotUri`, `GetStreamUri` quando elegível; vendor endpoints somente se fundamentados. Nenhuma mutação.
- **RTSP:** política separada de protocolo; scheme RTSP/RTSPS somente onde já suportado, host/porta exatos, sem redirects, protocolos auxiliares ou playlists arbitrárias. Credenciais em options do decoder, nunca URI/log. TCP, um frame, semáforo global 1, pixel cap e close. Sessão HTTPS aceita não autoriza RTSP. Imagem não inicia autenticação sem sessão aceita no mesmo escopo; auth nova exige decisão específica.
- **Limites de dados:** limites existentes são preservados. O corpo SOAP tem limite de 1 MiB.

## 7. Política unificada de autenticação

Estados de autenticação separados do status de resultado: `AUTH_SCOPE_UNKNOWN`, `AUTH_NEGOTIATION`, `AUTH_ACCEPTED`, `AUTH_REJECTED_FINAL`, `AUTHORIZATION_DENIED`.

401 anônimo pode ser challenge. O challenge Digest corretamente respondido não conta como nova tentativa lógica, mas cada troca física conta no budget. 401 após negociação encerrada é rejeição final; 403 é negação final. SOAP NotAuthorized permanece de causa desconhecida e não inicia autenticação de diagnóstico. Não alternar Digest/Basic/WSSE automaticamente.

D03 literal: no máximo 2 tentativas autenticadas lógicas por câmera: primária e no máximo uma secundária, somente se faltar fabricante confirmado/model/serial, sem recusa/negação final e dentro do budget. Uma família vendor por alvo. Sessão aceita pode fazer mais leituras dentro do mesmo escopo até recusa. Não autenticar exclusivamente por firmware, hostname ou imagem. Após rejeição/negação final, nenhuma operação autenticada posterior em vendor, ONVIF, snapshot ou RTSP; preservar evidência preauth e `PARTIAL_SUCCESS`. Não inferir permissão a partir de `status != FAILED`.

O estado é por linha/coleta; linhas com mesmo IP têm credenciais e sessões independentes e não são fallback umas das outras. MULTI deve preservar relatório até decidir snapshot; cancelar ou rejeitar não apaga evidências/tentativas anteriores.

## 8. Budget e cancelamento

Valores preservados: connect 3 s; read 7 s; ONVIF cumulativo 15 s; native cumulativo 10 s; soft deadline da câmera 45 s; snapshot HTTP 10 s; RTSP open 8 s; first frame 5 s; default de 0 retries e máximo configurável de 1 retry de aplicação elegível por operação; backoff 1 s. Não inventar teto global numérico ausente do plano.

Deadline monotônico criado antes de preauth e nunca reiniciado. Source budget conta discovery e handshake; global inclui inventário, fallback, snapshot, RTSP e espera por semáforo. Cada send/challenge/retry/chunk/nova etapa verifica restante; timeout é o menor valor entre timeout de política e budgets source/global remanescentes. Toda troca física conta.

Retry somente em leitura transitória idempotente, no máximo uma vez quando configurado; o default é zero. Excluir auth, TLS, refused, invalid, unsupported e erros determinísticos. Digest não é retry. Nenhum discovery equivalente/capability repetido.

`cancel_event` é verificado antes do cliente, entre fontes, antes de cada envio, durante fila/espera RTSP/chunks e antes do snapshot. MULTI deixa de submeter tarefas, cancela futures pendentes e sinaliza as ativas. Após retorno, uma tarefa ativa não inicia etapa nova; aguarda boundary seguro, fecha recurso e preserva parciais; não exporta lote incompleto. Sem matar threads e sem implementar D07.

`SOFT_DEADLINE` impede novos envios/etapas quando observado, mas chamada bloqueada pode passar de 45 s. `HARD_TIMEOUT` limita espera apenas onde a biblioteca suporta. Não prometer teto absoluto para DNS/TLS/decoder/call bloqueada.

## 9. Integridade e segurança de dados

- Rejeitar U+controls, ESC/C1/ANSI, surrogate e caracteres inválidos de XML/XLSX na entrada; defender saída terminal/writer para legado.
- Preservar Unicode válido e valor semântico; aplicar limite de tamanho antes de entrar no domínio. Não normalizar conteúdo hostil para uma identidade falsa.
- Proteger fórmula depois da sanitização, também com prefixo de espaços/controles. Isolar erro por célula/linha; fechamento de workbook/imagens/temporários via `try/finally`; preservar linhas válidas e sinalizar campo/linha incompatível.
- Recalcular status quando campo essencial inválido sem mudar `IDENTITY_V1`; não fabricar hostname, serial ou fabricante.
- Hikvision: remover `deviceName → hostname`; nenhum endpoint novo.
- XML: parser existente rejeita DTD via callback antes de expansão, encoding-independent; aceitar UTF-8/UTF-16LE/BE suportados; proibir entidade externa/file/network; malformed/incoherent falha controlada. Preservar limite de 64 KiB Hikvision, limites estruturais/texto/elementos; Zeep `forbid_dtd/entities/external=true`, `huge_tree=false`, imports locais. Limite SOAP 1 MiB aprovado.
- Preservar limites existentes para imagens vendor: 8 MiB e 40M pixels.

## 10. Configuração e dependências

Schema completo e encaminhamento das opções suportadas até componente consumidor; opção desconhecida não é silenciosamente ignorada. Arquivo de defaults opcional ausente usa defaults seguros; arquivo explicitamente solicitado ausente falha; mensagens de erro sanitizadas. Opções obsoletas são removidas/marcadas e config obsoleta falha.

As faixas estritas detalhadas na ficha PREP12-08 estão aprovadas. O default de retries é 0 e o máximo configurável é 1. Guardrails fixos, sem configuração, são workers 1–32, concorrência RTSP 1 e thumbnail 320×180/q75. Sem bool como int, NaN/Inf, timeout zero, coerção ou valores fora das faixas aprovadas. O schema de transporte por alvo também está aprovado.

PREP12-10: inventariar imports diretos; justificar `httpx`; declarar dependências diretas, inclusive `requests` se usado diretamente e Zeep/lxml quando APIs da fachada forem diretas. Especificar versões resolvidas exatas, transitivas, plataforma/Python e hashes, além de ferramentas/hooks de build. `pip freeze` de ambiente existente não é lock validado. Não instalar nem mudar dependências nesta atividade; ambiente limpo requer autoridade própria. Validação futura: Python 3.14/Windows, ambiente novo, `pip check`, regressão completa e preparação de packaging.

## 11. Requisitos de preparação P12

### PREP12-09 — preparação prévia

Consertar caminhos relativos a CWD; inventariar WSDL, recursos, hooks e DLLs locais de Zeep/lxml/PyAV/certificados/TOML; incluir somente itens comprovadamente necessários. Definir defaults embutidos somente leitura, config externa e diretório de usuário gravável para logs/temp fora do bundle. Startup falha controladamente se não houver path gravável. Destino XLSX permanece escolhido e não sobrescrito. Isso prepara, não valida o executável.

ONEDIR build e smoke pertencem à P12 autorizada, Windows 11 x64 sem Python instalado, cobrindo paths com espaços/acentos, pasta protegida, recursos, DLLs, certificados, logs/temp e destino corporativo. `PREP12-09` permanece `UNVERIFIED_RISK` até prova executável.

### PREP12-13 — validação offline vs real

Offline: fixtures estruturadas de discovery e capabilities/extensions, fluxo entrypoint até resolution/registry/adapter/fallback/CameraResult. Um `Manufacturer` injetado não é prova, não usar fixture para alegar suporte universal. Real: modelos/famílias somente em homologação autorizada. Finding não vira homologado só por testes offline.

## 12. Matriz integrada de testes

Teste completo, sem criar harness genérico, reutilizando testes existentes somente quando cobrirem a mesma semântica. Candidatos a reutilizar: `test_snapshot_pipeline.py`, `test_hikvision_isapi.py`, `test_vendor_http_budget.py`, `test_p2_i1_collection.py`, `test_vendor_registry_integration.py`, `test_p1_cli_flow.py`, `test_p1_vendor_first_strategy.py`, `test_p1_onvif_collector.py`, `test_p1_inventory_service.py`, `test_multi_workflow.py`, `test_excel_reader_sanitization.py`, `test_p5_concurrency.py`, `test_axis_hanwha_adapters.py`, `test_dahua_panasonic_adapters.py`, `test_bosch_onvif_fallback.py`, `test_p2_i1_sensitive_evidence.py`, `test_p1_domain.py`, `test_scaffold_structure.py`. Não atribuir cobertura sem verificar conteúdo.

| Critério | Aceite integrado obrigatório | Findings principais |
|---|---|---|
| A | SINGLE ONVIF seguro | 01, 03, 04 |
| B | MULTI ONVIF seguro e ledger preservado | 01, 03, 04, 05, 13 |
| C | HTTPS com certificado confiável | 01, 02 |
| D | Certificado inválido sem downgrade | 01, 02 |
| E | Todos redirects HTTP 30x bloqueados | 01, 02 |
| F | Sem proxy/netrc/credencial ambiental | 01 |
| G | Snapshot sem HTTP implícito | 02, 08 |
| H | 401/403 final impede qualquer auth posterior | 03 |
| I | Evidência parcial preservada | 03, 05 |
| J | Cancelamento antes de snapshot/RTSP impede essas etapas | 05 |
| K | Deadline exaurido impede novas requests | 04 |
| L | Caractere inválido no XLSX é isolado; linhas válidas persistem | 06 |
| M | Fórmula/ANSI/Unicode/tamanho longo tratados com segurança | 06 |
| N | `deviceName` nunca vira hostname | 07 |
| O | DTD/entity rejeitados em UTF-8/UTF-16; XML válido segue | 14 |
| P | Config chega ao runtime; config inválida falha antes da rede | 08 |
| Q | Fluxo real entrypoint→discovery→resolução, incluindo hint P1 aprovado→registry→adapter/fallback | 13 |
| R | Credenciais/sessão/auth/budget/evidência isolados sob concorrência e ordem | 03–05 |
| S | RUN_ID e logs sem segredo/rollover efetivo | 11 |
| T | Regressões SINGLE/MULTI/P5 e identidade de 14 campos | 03–08, 13 |
| U | Recursos fechados em sucesso/falha/cancelamento | 01–06, 09, 11 |
| V | Suíte completa Python 3.14 sem falhas, skipped ou deselected | Todos aplicáveis |
| W | Dependências reproduzíveis e preparação de packaging | 09–10 |

O gate V requer diretório temporário funcional e execução integral. Os 7 casos inconclusivos atuais permanecem sem nomes; a futura execução deve reportar seleção/resultado integral sem inferir quais eram. Baseline histórica de 220 não substitui nova execução. Não exigir câmera real para gates offline.

## 13. Dependências e ordem de execução

Ownership sem sobreposição; interfaces comuns fechadas antes de paralelizar. Uma atividade integrada, sem cards humanos separados.

1. **Integrador central/contexto/interfaces/strategy/workflows/main:** definir interface imutável do transporte/contexto, ledger, deadline/cancel e fluxo SINGLE/MULTI; contratos incluem snapshots.
2. **Transporte/fachada ONVIF:** construir sobre interfaces fechadas; realizar segurança Zeep/requests pré-I/O e política unificada.
3. **Vendor/dados/Hikvision — ownership único:** consolidar limites de entrada, PREP12-07 e PREP12-14 sem conflito entre parser e adapters.
4. **XLSX/domínio:** mapear segurança de texto e falha isolada com identidade canônica.
5. **Config/build/log:** conectar opções e preparação offline/deps/logging.
6. **Integração de testes:** fluxo estruturado real offline, segurança/concorrência e regressão acumulada.
7. **Revisão independente:** findings de segurança corrigidos e reconciliados.
8. **Documentação/readiness:** reconciliação e reavaliação pré-P12 sem executar P12.

Dependências direcionais: transporte e context (01/02/03/04/05/08); fluxo central depende das interfaces e do transporte; snapshots dependem de auth/context; vendor XML/dados depende do contexto e validação comum; config conecta políticas sem mudar limites; packaging depende de dependências/paths; docs dependem do resultado integrado. PREP12-11 está incluído no pacote e mantém a prioridade histórica `POST_DELIVERY_BACKLOG`.

## 14. Gates e definição de pronto

1. `GATE_1 = IMPLEMENTATION_COMPLETE`: contrato implementado offline na única atividade e inventário de escopo conferido.
2. `GATE_2 = INTEGRATED_REGRESSION_PASS`: critérios aplicáveis, inclusive V, passam; nenhum skipped/deselected e temp funcional.
3. `GATE_3 = SECURITY_FINDINGS_CLEARED`: revisão independente concluída; findings materiais tratados; PREP12-01/02/03 corrigidos e validados.
4. `GATE_4 = PRE_P12_READINESS_REASSESSMENT`: reavaliar bloqueio sem executar P12. 01–03 precisam estar limpos antes de iniciar P12. PREP12-09 continua pendente de build P12; PREP12-13 pode estar offline pronto, mas homologação real pendente.
5. `GATE_5 = USER_APPROVAL_FOR_PUBLICATION`: pedir aprovação de publicação somente depois de tornar o pacote concreto e revisável.

Não criar 14 aprovações humanas. Fechar implementação não é homologar produto. `IMPLEMENTED_OFFLINE`, `PUBLISHED`, `VALIDATED_REAL_CAMERA` e `OPERATIONALLY_APPROVED` são estados distintos; contrato aprovado não marca nenhum deles.

## 15. Riscos residuais

- Deadline é soft quando API bloqueia; não há garantia absoluta para DNS/TLS/decoder.
- Câmeras com certificados não confiáveis falham fechado até decisão de confiança; não haverá downgrade.
- ONVIF SDK não permite injeção direta via `ONVIFClient`; fachada precisa demonstrar cobertura de requests reais e compatibilidade com APIs internas.
- PREP12-09 é risco ainda não verificado até executar ONEDIR em P12.
- PREP12-13 não demonstra interoperabilidade de modelos reais sem homologação autorizada.
- Faixas estritas de configuração, `backupCount >= 1`, schema de transporte TOML por alvo e limite SOAP de 1 MiB foram aprovados com este contrato; a aprovação não comprova sua implementação nem valida P12.
- D07 permanece diferida; nenhum resultado aqui autoriza trabalho nela.

## 16. Pendências de validação futura

| Estágio | Evidência ainda necessária |
|---|---|
| PRE_P12_REMEDIATION | implementação, testes unitários/integrados, regressão completa Python 3.14, revisão independente e reavaliação de readiness |
| P12_BUILD | ONEDIR real Windows 11 x64 sem Python, imports/WSDL/DLL/cert/config/log/temp/destino e startup em path protegido |
| REAL_CAMERA_HOMOLOGATION | interoperabilidade READ_ONLY por modelo/família sob autorização explícita; sem credenciais reais nesta atividade |
| PRE_P12_REMEDIATION | PREP12-11 incluído no pacote atual; validação do rollover e retenção efetivos |

Resultados atuais da auditoria são distintos: 213 passed, 7 inconclusivos/deselecionados, Ruff PASS, `pip check` PASS; câmera/build NOT_RUN. Não declarar regressão integral atual.

## 17. Plano integrado de implementação

O trabalho de implementação autorizado limita-se à remediação offline deste contrato. Fases internas: fechar interfaces/contexto; implementar transporte/auth/budget/cancel; integrar workflow central e snapshots; corrigir vendors/XML/XLSX e seleção de fabricante; conectar config/log e preparação de dependências/packaging; rodar testes ponta a ponta e suíte integral; revisão independente; atualizar documentos e reavaliar readiness pré-P12. Owners funcionais listados na seção 13 evitam escritores simultâneos nos mesmos recursos. A autorização não inclui build P12, câmeras reais, publicação ou fechamento de fase.

## 18. Decisões que exigem autorização específica

- Aprovação deste contrato e autorização offline são decisões distintas; ambas estão concedidas nos limites registrados neste documento.
- Instalar ou alterar versões/dependências, criar ambiente limpo, build P12, câmeras reais/credenciais, commit/push, publicar, fechar fase e declarar aprovação operacional requerem autoridade específica.
- Ampliar resiliência/paralelismo; autenticação HTTP/RTSP fora de D03 ou novas credenciais; mudar `CameraResult`, identidade ou contratos canônicos; adicionar endpoints; declarar suporte universal; garantir hard timeout absoluto; reabrir D07 requer decisão própria.
- Schema TOML por alvo/componente/porta, teto SOAP de 1 MiB, faixas estritas de configuração e `backupCount >= 1` estão aprovados neste contrato.
- A autorização concedida cobre correções offline contidas no contrato e seus testes; gates globais continuam necessários. Build P12, câmera real/credenciais, publicação, fechamento de fase, commit/push e aprovação operacional continuam fora da autorização.

```text
CONTRACT_STATUS = APPROVED_WITH_ADJUSTMENTS
USER_CONTRACT_APPROVAL = GRANTED
IMPLEMENTATION_AUTHORIZATION = GRANTED_FOR_OFFLINE_REMEDIATION_ONLY
PREP12-11 = INCLUDED_IN_CURRENT_PACKAGE
DEFAULT_RETRIES = 0
MAX_CONFIGURED_RETRIES = 1
PER_TARGET_TRANSPORT_SCHEMA = APPROVED
SOAP_BODY_LIMIT = 1_MIB
STRICT_CONFIGURATION_RANGES = APPROVED
LOG_BACKUP_COUNT_MIN = 1
D00_D06 = PRESERVED
D07 = DEFERRED
CAMERA_RESULT = 14_FIELDS
IDENTITY = IDENTITY_V1
P1 = CLOSED
P2 = IN_PROGRESS
P12_READINESS = BLOCKED
BLOCKING_FINDINGS = PREP12-01, PREP12-02, PREP12-03
REAL_CAMERA_VALIDATION = NOT_RUN
P12_BUILD = NOT_RUN
NEXT_GATE = OFFLINE_REMEDIATION_INTEGRATED_GATES
```
