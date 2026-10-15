# Registro de findings — auditoria pré-P12

Baseline `b4c67f74bead61a40ab9037934f994dad7dfe701`; decisão `P12_READINESS=BLOCKED`. Evidências/ref. são as recebidas no handoff e verificadas contra o baseline.

| ID | Severidade | Categoria | Status | Prioridade | Blocker P12 |
|---|---|---|---|---|---|
| PREP12-01 | HIGH | SECURITY/ONVIF_TRANSPORT | CONFIRMED | MUST_FIX_BEFORE_P12 | YES |
| PREP12-02 | HIGH | SECURITY/SNAPSHOT_TRANSPORT | CONFIRMED | MUST_FIX_BEFORE_P12 | YES |
| PREP12-03 | HIGH | SECURITY/AUTHENTICATION_SCOPE | CONFIRMED | MUST_FIX_BEFORE_P12 | YES |
| PREP12-04 | MEDIUM | CORRECTNESS/TIME_BUDGETS/SCALE | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-05 | MEDIUM | CORRECTNESS/CANCELLATION | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-06 | MEDIUM | MULTI_XLSX/UNTRUSTED_DATA | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-07 | MEDIUM | FUNCTIONAL_CORRECTNESS/DOMAIN_MAPPING | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-08 | MEDIUM | CONFIGURATION/OPERABILITY | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-09 | MEDIUM | P12_PACKAGING/DISTRIBUTION | UNVERIFIED_RISK | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-10 | MEDIUM | DEPENDENCIES/REPRODUCIBILITY | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-11 | LOW | LOGGING/RESOURCE_LIMIT | CONFIRMED | POST_DELIVERY_BACKLOG | NO |
| PREP12-12 | LOW | DOCUMENTATION/CONTINUITY | CONFIRMED | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-13 | MEDIUM | VENDOR_COVERAGE/TEST_REALISM | UNVERIFIED_RISK | RECOMMENDED_BEFORE_DELIVERY | NO |
| PREP12-14 | MEDIUM | SECURITY/XML_PARSING | LIKELY | RECOMMENDED_BEFORE_DELIVERY | NO |

## PREP12-01 — ONVIF sem transporte governado

- **FILE / LINE:** `src/cam_scanner/cameras/onvif/adapter.py:40`; `src/cam_scanner/cameras/preauth.py:75`, `src/cam_scanner/snapshot/onvif.py:103`, `src/cam_scanner/snapshot/rtsp.py:93`; SDK `operator.py:226–227`, `client.py:138`; Zeep `transports.py:84`.
- **EVIDENCE:** ONVIFClient sem transporte protegido; SDK cria requests.Session e define `verify_ssl`, cujo default é False; sessão mantém `trust_env=True`; POST Zeep não desativa redirects; app não tem allowlist antes dos requests SDK.
- **REPRODUCTION:** introspecção offline `_create_session(verify_ssl=False)` mostrou `trust_env=True`/`verify=False`. Nenhum exploit de proxy/redirect foi feito.
- **IMPACT:** proxy/netrc pode interferir; redirect pode ampliar destino/reenviar SOAP; TLS não é imposto.
- **ROOT_CAUSE:** confiar na abstração SDK sem governar sessão/requisições.
- **RECOMMENDED_FIX:** governar transporte no limite atual: `trust_env=False`, TLS verificado, política scheme/host/port, bloquear redirects pré-envio, limites de resposta e fechar recursos.
- **REQUIRED_TEST:** fixture requests/Zeep real: proxy/netrc, 301/302/307/308, XAddr divergente/userinfo, certificado ruim, limites/close e requests efetivas.

## PREP12-02 — Snapshot HTTP fixo

- **FILE / LINE:** `src/cam_scanner/snapshot/manufacturer.py:55`; `src/cam_scanner/snapshot/onvif.py:105–110,132`; teste `tests/test_snapshot_pipeline.py:208`.
- **EVIDENCE:** vendor monta `http://{host}:80`; ONVIF fixa porta 80 e `use_https=False`; `_target_http_url` só aceita HTTP :80; CameraTarget não tem config HTTP explícita; teste espera HTTP.
- **REPRODUCTION:** inspeção/caminho testado; `verify=True` em HTTP não fornece TLS.
- **IMPACT:** imagem/credencial sem proteção; câmera HTTPS não atende snapshot; após Hikvision HTTPS pode abrir HTTP, contrariando D04.
- **ROOT_CAUSE:** política de snapshot fixa e separada.
- **RECOMMENDED_FIX:** transporte explícito por alvo, preferir HTTPS validado, HTTP só autorizado; sem downgrade.
- **REQUIRED_TEST:** HTTPS válido; TLS inválido sem downgrade; recusar HTTP não configurado; permitir HTTP explicitamente; rejeitar URL/portas não autorizadas.

## PREP12-03 — Autenticação após recusa final

- **FILE / LINE:** `src/cam_scanner/application/single_workflow.py:39`; `multi_workflow.py:146`; projeção MULTI `collect_one`.
- **EVIDENCE:** SINGLE/MULTI tiram snapshot em status != FAILED. Preauth pode guardar fabricante e AUTH_REJECTED/AUTHORIZATION_DENIED com PARTIAL_SUCCESS; provider cria cliente autenticado. MULTI descartou histórico de tentativas.
- **REPRODUCTION:** `tests/test_p1_cli_flow.py:79` cobre evidência parcial + recusa e PARTIAL_SUCCESS; linha 39 chama `capture_one`. Interrupção SnapshotService só ocorre depois dessa tentativa. Sem alvo externo.
- **IMPACT:** login após rejeição final/403, lockout e violação D03; budget não compartilhado.
- **ROOT_CAUSE:** política auth local por subsistema e status agregado usado como autorização.
- **RECOMMENDED_FIX:** propagar rejeição ponta a ponta e impedir requests autenticadas posteriores; preservar contexto no MULTI.
- **REQUIRED_TEST:** SINGLE/MULTI com evidência parcial + 401 final/403; zero snapshot/RTSP posterior; distinguir challenge Digest de recusa final.

## PREP12-04 — Sem budget cumulativo

- **FILE / LINE:** `src/cam_scanner/cameras/strategy.py:47`; `preauth.py:117–118`; `hikvision.py:60,152`; `_http_utils.py`.
- **EVIDENCE:** strategy sem deadline/contador; preauth duas operações + GetServices/GetCapabilities SDK; Hikvision timeout fixo e cap de bytes, não deadline; snapshots sem budget comum. Testes cobrem helper/Axis/Dahua, não cadeia/Hikvision.
- **REPRODUCTION:** inspeção/comparação; sem execução encadeada.
- **IMPACT:** consulta/cancelamento pode exceder 45s, iniciar estágios sem resto; previsibilidade menor para 2300.
- **ROOT_CAUSE:** budget não propagado.
- **RECOMMENDED_FIX:** propagar deadline/contador, checar antes de cada operação, limitar timeout restante e incluir handshake/discovery; mesmo helper no Hikvision.
- **REQUIRED_TEST:** fake clock preauth→vendor→fallback→snapshot; nenhuma request após deadline, contar exchanges, evidência e semântica soft/hard.

## PREP12-05 — CANCELLED não para todas as fases

- **FILE / LINE:** `src/cam_scanner/cameras/strategy.py:55,136–138`; `preauth.py:98,148`; workflow.
- **EVIDENCE:** preauth pode retornar CANCELLED e strategy continua; vendor só para em rejeição/SUCCESS e segue ONVIF; workflow pode snapshot pois CANCELLED != FAILED. Executor aguarda tarefas rodando.
- **REPRODUCTION:** inspeção; `tests/test_p2_i1_collection.py:195` cobre cancelamento só no ONVIF final, não etapa anterior/snapshot.
- **IMPACT:** Ctrl+C permite consultas adicionais; encerramento aguarda tarefas ativas.
- **ROOT_CAUSE:** cancelamento não é condição comum de parada.
- **RECOMMENDED_FIX:** checar entre fases e antes snapshot; preservar evidência, sem prometer interrupção forçada de thread.
- **REQUIRED_TEST:** cancelamento em create-client/preauth/vendor/ONVIF/espera RTSP; nenhuma fase posterior, recursos liberados.

## PREP12-06 — U+0001 pode abortar XLSX

- **FILE / LINE:** `src/cam_scanner/domain/models.py:111`; `excel/writer.py:85,148,182`; openpyxl `cell.py:164–165`.
- **EVIDENCE:** domínio rejeita secrets/URLs/placeholders mas aceita U+0001; JSON vendor pode carregar; `_cell` trata vazio/fórmula, conversão fora do bloco protegido; openpyxl lança IllegalCharacterError.
- **REPRODUCTION:** análise: `model='M\\u0001X'` passa `is_valid_evidence_value`, mas `check_string` rejeita. Nenhum XLSX gerado.
- **IMPACT:** uma câmera aborta relatório; controles podem chegar ao terminal.
- **ROOT_CAUSE:** domínio não garante compatibilidade dos canais nem isolamento por linha na serialização.
- **RECOMMENDED_FIX:** rejeitar/normalizar controles na entrada e exportação; preservar linhas e sinalizar célula/linha inválida.
- **REQUIRED_TEST:** XML controls, ESC ANSI, strings longas, fórmulas, Unicode/lote misto, arquivo válido sem abort global.

## PREP12-07 — deviceName equivale incorretamente a hostname

- **FILE / LINE:** `src/cam_scanner/cameras/manufacturers/hikvision.py:216`; contrato P2 §10.
- **EVIDENCE:** `devicename` é mapeado a hostname, embora contrato diga que deviceName não é hostname.
- **REPRODUCTION:** parser offline `<deviceName>Camera Label</deviceName>` produz hostname.
- **IMPACT:** rótulo configurável exportado como identidade de rede.
- **ROOT_CAUSE:** campos semanticamente distintos equiparados.
- **RECOMMENDED_FIX:** não preencher hostname de deviceName; usar operação documentada correta se autorizada; não ampliar contrato por este defeito.
- **REQUIRED_TEST:** deviceName deixa hostname ausente; só fonte correta preenche.

## PREP12-08 — Configuração ignorada

- **FILE / LINE:** `src/cam_scanner/config/loader.py:20,27`; `src/cam_scanner/main.py:28–33`.
- **EVIDENCE:** loader usa apenas `concurrency.default_max_workers`; outras opções de collection/snapshot/log/retry/RTSP não chegam aos componentes; main passa só workers.
- **REPRODUCTION:** `request_timeout_seconds` não chega aos collectors.
- **IMPACT:** operador acredita que timeout/retenção/snapshot mudou, mas defaults executam.
- **ROOT_CAUSE:** scaffold confundido com configuração efetiva.
- **RECOMMENDED_FIX:** ligar e validar opções suportadas; remover/marcar opções inoperantes; não aceitar silenciosamente.
- **REQUIRED_TEST:** valores chegam ao componente final; tipos/faixas inválidos rejeitados; defaults sem arquivo.

## PREP12-09 — Packaging não validado

- **FILE / LINE:** `packaging/cam_scanner.spec:8`; `config/loader.py:33`; `logging/setup.py:16–18`.
- **EVIDENCE:** binaries/datas/hiddenimports vazios, sem hooks; ONVIF/WSDL, DLLs PyAV/config não validados; config/logging deriva de `__file__`, logger precisa gravar ali.
- **REPRODUCTION:** inspeção apenas, sem build. Não se afirma que hooks ou exe necessariamente falham.
- **IMPACT:** recursos/imports/DLLs/config ausentes ou falha em pasta protegida.
- **ROOT_CAUSE:** scaffold sem convenções validadas de config/dados graváveis.
- **RECOMMENDED_FIX:** fechar spec e convenções config embutida/externa e dados graváveis em P12; verificar hooks efetivos antes de coleta indiscriminada.
- **REQUIRED_TEST:** ONEDIR Win11 x64 sem Python, paths com espaços/acentos e pasta protegida; ONVIF/WSDL, Zeep/lxml, PyAV/DLL, openpyxl/Pillow/Rich, TOML, certificados, logs/temp e destino corporativo.

## PREP12-10 — Dependências sem reprodução garantida

- **FILE / LINE:** `pyproject.toml:11`.
- **EVIDENCE:** dependências produto/dev sem versões, sem lock/constraints; código importa requests diretamente, manifesto declara httpx e requests é transitiva do SDK.
- **REPRODUCTION:** inventário manifesto e comparação de versões no venv reutilizado.
- **IMPACT:** instalação/build pode alterar comportamento SDK/hooks; pip check atual não demonstra repetibilidade.
- **ROOT_CAUSE:** scaffold sem conjunto reprodutível.
- **RECOMMENDED_FIX:** conjunto aprovado reprodutível Python 3.14/Windows e dependências diretas.
- **REQUIRED_TEST:** ambiente autorizado novo, pip check, regressão e packaging smoke. Nenhuma instalação nesta auditoria.

## PREP12-11 — Rotação de log não efetua rollover

- **FILE / LINE:** `src/cam_scanner/logging/setup.py:27`; stdlib Python 3.14.
- **EVIDENCE:** RotatingFileHandler `maxBytes=10 MiB`, `backupCount=0`; doRollover só rotaciona com backupCount>0; zero reabre em append.
- **REPRODUCTION:** inspeção stdlib; nenhum log grande criado.
- **IMPACT:** arquivo supera limite; retenção por idade ocorre só na próxima execução.
- **ROOT_CAUSE:** rotação desabilitada embora maxBytes definido.
- **RECOMMENDED_FIX:** rollover/truncamento/retenção efetivos.
- **REQUIRED_TEST:** exceder limite em temp e verificar arquivos/tamanhos.

## PREP12-12 — Documentação de entrada inconsistente

- **FILE / LINE:** `README.md:7,9`; `docs/continuity/planning/ROADMAP.md:8–16`; `docs/continuity/PROJECT_STATE.md`.
- **EVIDENCE:** README diz MULTI/adapters/snapshots/XLSX fora da slice e P1 aberta; roadmap mantém planejado enquanto PROJECT_STATE relata P3–P11 integradas offline.
- **REPRODUCTION:** comparação cruzada com snapshot/código.
- **IMPACT:** confusão de escopo, integração offline e fechamento/homologação.
- **ROOT_CAUSE:** entrypoints ficaram desatualizados após atualização central de continuidade.
- **RECOMMENDED_FIX:** reconciliar capacidades, limites e estado sem inferir fechamento/homologação.
- **REQUIRED_TEST:** revisão README↔roadmap↔execution plan↔PROJECT_STATE.

## PREP12-13 — Caminho padrão pode não exercitar adapters

- **FILE / LINE:** `src/cam_scanner/cameras/strategy.py:74`; `preauth.py:20,360`; `tests/test_vendor_registry_integration.py:46–49`.
- **EVIDENCE:** manufacturer inicia None; adapter só após resolução pré-auth; CameraTarget/XLSX não tem manufacturer; resolver promove chaves fortes, namespace/model/realm insuficientes. Teste injeta Manufacturer.
- **REPRODUCTION:** sem chave forte, manufacturer=None e ONVIF genérico. Sem respostas reais novas.
- **IMPACT:** registry de seis não prova fluxo padrão vendor; ONVIF pode ainda identificar.
- **ROOT_CAUSE:** fixtures sintéticas demonstram somente evidência fornecida.
- **RECOMMENDED_FIX:** fixtures GetCapabilities/extensões representativas e homologação real autorizada; hint de contrato só se necessário; não promover substring a sinal forte.
- **REQUIRED_TEST:** cada família via entrypoint→discovery→adapter e fallback honesto.

## PREP12-14 — Filtro DTD sensível a encoding

- **FILE / LINE:** `src/cam_scanner/cameras/manufacturers/hikvision.py:211`; `tests/test_hikvision_isapi.py:241`.
- **EVIDENCE:** filtro ASCII procura `<!DOCTYPE`/`<!ENTITY`, depois ElementTree aceita outros encodings; UTF-16 intercala NUL e pode contornar filtro. Teste atual é ASCII.
- **REPRODUCTION:** bypass proposto, não executado; nenhum XXE/leitura externa/exaustão demonstrados.
- **IMPACT:** provável bypass de política DTD, XXE não confirmado.
- **ROOT_CAUSE:** substring pré-parser sem considerar encoding.
- **RECOMMENDED_FIX:** rejeição encoding-independent de DTD/entity ou restringir explicitamente encodings.
- **REQUIRED_TEST:** DTD/entity UTF-8/UTF-16LE/BE e encodings aceitos; XML válido/namespaces, limites de tamanho/expansão.

```text
CRITICAL=0; HIGH=3; MEDIUM=9; LOW=2
MUST_FIX_BEFORE_P12=PREP12-01, PREP12-02, PREP12-03
RECOMMENDED_BEFORE_DELIVERY=PREP12-04, PREP12-05, PREP12-06, PREP12-07, PREP12-08, PREP12-09, PREP12-10, PREP12-12, PREP12-13, PREP12-14
POST_DELIVERY_BACKLOG=PREP12-11
P12_READINESS=BLOCKED
```
