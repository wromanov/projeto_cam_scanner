# ASTRA — Contrato P0: correções obrigatórias de compatibilidade Viewer

```text
PROJECT_ID = projeto_cam_scanner
ACTIVITY_ID = CAM_SCANNER_ASTRA_CONTRACT_FINALIZATION_02
PARENT_ACTIVITY = CAM_SCANNER_ASTRA_CONTRACT_CLOSURE_01
CONTRACT_ID = ASTRA_P0_REQUIRED_CORRECTIONS_V2
DOCUMENT_STATUS = PROPOSED
CONTRACT_STATUS = READY_FOR_FINAL_NORMATIVE_APPROVAL
TECHNICAL_DIRECTION_STATUS = APPROVED_BY_USER_CARD_FINALIZATION_02
APPROVAL_STATUS = PENDING_FINAL_NORMATIVE_DELTAS
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
REAL_CAMERA_ACCESS = NOT_AUTHORIZED
MODEL_REQUESTED = ASTRA
MODEL_RUNTIME_ATTESTATION = UNAVAILABLE; nenhuma reconfiguração alegada
EXECUTION_MODE = DIRECT
```

**P0/P1/P2 são prioridades deste adendo**, não as fases P0–P12 do roadmap. P0/P1 históricos permanecem CLOSED e a fase P2 histórica conserva seu estado. O usuário aprovou a direção técnica P0/P1 no Card CAM_SCANNER_ASTRA_CONTRACT_FINALIZATION_02. Esta revisão fecha propostas para aprovação final dos deltas normativos; execução, câmera e HTTP real continuam sem autorização.

## 1. Contexto, evidência e baseline

A auditoria de 27/10/2026 concluiu CONDITIONAL_GO para inventário útil/parcial com interfaces e permissões existentes; viewer-only operacional permanece NOT_VERIFIED. F01–F09 estão recuperados na matriz da seção 14, com disposição proposta, sem novo clearance ou repetição da auditoria.

Baseline obrigatória: checkout local `projeto_cam_scanner_pre_p12_remediation`, branch `feature/pre-p12-unified-remediation`, HEAD `37bc8c4cc718559fc1e6f39a9b8a1145563a551e` **mais alterações locais R2 preexistentes**. A pasta originalmente aberta e o master remoto não substituem esse conteúdo. Na auditoria anterior, master remoto estava em b4c67f7; isso é fato histórico, não consulta remota refeita neste adendo.

Fontes: [P1 histórico](P1_SINGLE_MINIMUM_VERTICAL_SLICE.md), [P2 histórico aprovado](P2_COLLECTION_STRATEGY_EXPANSION.md), [PRE-P12](PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md), [R2 aprovado](VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT_R2.md), [validação offline R2](../audit/VENDOR_FIRST_RUNTIME_CORRECTION_R2_VALIDATION_2026-10-19.md), [estado vigente](../continuity/PROJECT_STATE.md). O parecer original da atividade CAM_SCANNER_ASTRA_FEASIBILITY_AUDIT_01 foi entregue ao chat Projeto Scanner 2.0; não há arquivo canônico desse parecer no checkout. Esta matriz persiste os fatos necessários à implementação sem exigir histórico do chat.

Os 389 testes/Gate 3 e build R2 são evidências históricas offline; não homologam contas viewer. Nesta autoria não houve teste funcional, instalação, build ou câmera. Hashes abaixo são dos bytes locais, não Git blob IDs:

| Arquivo de referência | SHA-256 na entrada da revisão V1 |
|---|---|
| `docs/contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md` | `7c8c2f46e98b5dbc01bc877e153f7aea17751aa5fa4cebf629bb1cdcca18af22` |
| `docs/contracts/P2_COLLECTION_STRATEGY_EXPANSION.md` | `3506dfe52bb67e930bf40b81631918835bc27186a899f47594baa166d0bd2d61` |
| `docs/contracts/PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md` | `cdea845c70342e51afad3b06b8c77f9e188099a189eade01be9bcf626267b3fa` |
| `docs/contracts/VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT_R2.md` | `5d401f2d336abe9a39f7ce49374885c8e539e48cca78aca55dc381f4384bfdf6` |
| `src/cam_scanner/cameras/strategy.py` | `7adc29c569a15dbfd3a6b68c7f1a44657719b188365211f1ed4e8dae5266d64b` |
| `src/cam_scanner/cameras/transport.py` | `3be782bead4f99955b06f8b25c11ab9ac2a1326420f0115c7dba19d373ec8cab` |
| `src/cam_scanner/application/collection_context.py` | `abb255a175c7164673555dd65b3148d8e8efe3718df8ef509b1f6a7e74272a1c` |
| `src/cam_scanner/domain/models.py` | `d9b0983607821a109718227f8010b29ac281c6a49e67958de00e626df9a96525` |
| `tests/test_vendor_first_runtime_correction_r2.py` | `42d2b6faa03bd156d5d305376901a5cef16cc58b5d0a86dc640b320b11d570d5` |

Pacote R2 conferido na auditoria antecedente: EXE SHA-256 `0E873442D5B3E1D8A4593D991AB8A3E50F6F77782C0945F16232706A365E4892`; manifesto `29D356C4524DE527EB5C81D34ED4A17D74ED5BE2AF9EE60A052970CC450B3958`; 265/265 correspondências. Não foi revalidado ou reconstruído aqui. Na revisão V1, um inventário de preservação de 112 arquivos governados foi capturado em memória na entrada para comparar a escrita estritamente documental; não contém senhas nem artefatos operacionais privados.

## 2. Objetivo e comportamento de saída

Corrigir seleção por menor privilégio, participação de fonte parcial, testes de ACL, scheme real e rastreabilidade. Usar exclusivamente serviços já disponíveis e credenciais do próprio alvo. IP, usuário e senha não garantem acesso a todos os dados.

| Dados observados | Resultado esperado |
|---|---|
| Fabricante observado forte, modelo e serial válidos, sem conflito essencial | SUCCESS conforme IDENTITY_V1, mesmo que firmware/imagem opcionais faltem. |
| Ao menos um dado útil validado, mas identidade incompleta ou conflitante | PARTIAL_SUCCESS; manter proveniência e lacunas. Hint não fecha identidade. |
| Nenhum dado útil de identidade | FAILED com causa normalizada; mera porta/serviço alcançável ou declaração não vira inventário. |
| Cancelamento observado | CANCELLED; evidências anteriores preservadas; nenhuma nova etapa de rede. |

## 3. Escopo IN/OUT

**IN:** P0-01 Axis; P0-02 Panasonic; P0-03 ACL sintética; P0-04 proveniência HTTP/HTTPS; P0-05 baseline. Inclui mudanças locais indispensáveis nas interfaces internas, allowlists de operações e fixtures, quando futuramente autorizadas.

A política centralizada prospectiva, suas fronteiras de escrita e ACs estão exclusivamente no [contrato de transporte](ASTRA_CENTRALIZED_TRANSPORT_IMPLEMENTATION_CONTRACT.md). P0-04 corrige proveniência; não implementa sozinho seleção de perfis por lote.

**OUT:** novos fabricantes, requests de rede só para opcionais, novos endpoints exceto os dois métodos Axis propostos no CGI existente; model_hint (P1 separado), hostname/DNS de entrada, novo auth/mecanismo/algoritmo, configuração em equipamentos, novos perfis de mídia, RTSP, dependências/build/publicação/Git consequencial. Não alterar os contratos históricos nesta implementação: o delta normativo deve ser aprovado como aditivo prospectivo.

## 4. Fronteiras candidatas e ownership futuro

| Responsabilidade única | Arquivos candidatos |
|---|---|
| Integrador de estratégia/contexto | `src/cam_scanner/cameras/strategy.py`, `application/collection_context.py`, `application/inventory_service.py`, `domain/models.py`; integração em `main.py` somente se indispensável. |
| Operações e parsers nativos | `cameras/manufacturers/axis.py`, `panasonic.py`, `_http_utils.py`; operação dos demais adapters só para proveniência, sem novos endpoints. |
| Transporte/proveniência | `cameras/transport.py`, leitores de metadados nos adapters e `terminal/ui.py`, `excel/writer.py` estritamente para representação correta. |
| Testes | Responsável pelos testes coordena `test_axis_hanwha_adapters.py`, `test_dahua_panasonic_adapters.py`, `test_collection_context.py`, `test_target_transport.py`, `test_pre_p12_transport_integration.py`, `test_vendor_first_runtime_correction_r2.py`, fluxos SINGLE/MULTI e sanitização. |

Paths são relativos à raiz Git confirmada em runtime; não hardcodear paths de máquina no produto. Um owner por arquivo compartilhado; alterações simultâneas de outros agentes/usuário devem ser acomodadas, nunca revertidas.

## 5. Invariantes, transporte e autenticação

1. Zero Set/reboot/escrita de configuração, criação/elevação de usuário, habilitação de serviço, firmware ou instalação de certificado na câmera. Não realizar testes negativos de escrita em hardware.
2. Manter CameraResult com exatamente 14 campos e IDENTITY_V1. CollectionReport é agregado canônico; dados observados e declarados separados.
3. Preservar destino/componente/porta, sessões por linha, ledger, budgets/deadline/cancelamento e limites de corpo existentes. Não reconstruir transporte nem SDK.
4. HTTPS verifica certificado. TLS_ERROR fecha toda rede do contexto, sem verify=False, TOFU, novo contexto ou HTTP subsequente. HTTP só se escolhido antes de I/O por regra exata autorizada. O contrato TRANSPORT propõe compilar um grupo fechado de IPs em regras exatas, com seleção e autorização próprias; não concede autorização geral de parque.
5. Transporte e auth são eixos distintos: HTTPS não obriga Basic; HTTP Digest não é WSSE. P0 não acrescenta mecanismos ou algoritmos. Helper nativo atual MD5/MD5-sess com qop auth/ausente; demais desafios são classificados como não suportados sem replay. WSSE atual ONVIF permanece; extensões seguem gate AUTH-EXT da seção 8.
6. Até duas tentativas autenticadas lógicas por câmera; uma família vendor; secundária apenas para identidade essencial ausente, sem rejeição/negação final e dentro do orçamento. Leituras públicas não consomem login nem geram AUTH_ACCEPTED; toda troca física consome budget/contagem.
7. 401 Digest de negociação de uma operação autenticada aprovada não é 401 final. 403, 401 final e NotAuthorized autenticado fecham o escopo conforme PRE-P12. Não trocar método/fabricante/mecanismo para descobrir permissões.
8. Nenhuma senha, username por padrão, URL completa, header/body/exceção bruta em log, diagnóstico, XLSX, evidência, repr ou temporário. Métodos/operações usam valores limitados e permitidos. Campos ecoando credenciais são rejeitados.

## 6. Fluxos e interfaces propostas

### P0-01 — Axis Viewer Compatibility

**Evidência focal:** o contrato V1 registra getAllProperties Operator. A [especificação BDI](https://developer.axis.com/vapix/network-video/basic-device-information/) indica nível Anonymous nos outros dois métodos; o CGI e exemplos também admitem credenciais. A [orientação de autenticação](https://developer.axis.com/vapix/authentication/) descreve primeira chamada sem credencial e challenge HTTP. Isso fundamenta negociação genérica, mas não identifica combinação de modelo/firmware/permissões Viewer autenticada para esta operação. Consulta pontual: 27/10/2026, sem repetir a auditoria. Suporte BDI/AXIS OS e exemplo 1.2 não garantem disponibilidade em todo equipamento.

**Plano fechado proposto:**
- Operações permitidas, exclusivamente POST JSON em `/axis-cgi/basicdeviceinfo.cgi`: getSupportedVersions, getAllUnrestrictedProperties e o getAllProperties já existente. Não usar API Discovery/param.cgi ou adivinhar endpoints para este escopo.
- Default interno VIEWER_SAFE: enviar sem Authorization, WSSE, credencial em JSON, cookie autenticado ou auth hook. A sessão pública é isolada e requests usam `authenticated=False`; a estratégia não chama auth.begin só por selecionar Axis.
- Se suporte 1.2 já foi observado na mesma coleta, reutilizar. Senão executar uma única getSupportedVersions anônima, com method=getSupportedVersions e sem apiVersion nesse request conforme a interface documentada; validar JSON limitado e apiVersions como lista de strings. Se contiver exatamente 1.2, selecionar essa versão e executar uma única getAllUnrestrictedProperties. Não enumerar versões ou tentar major futuro por suposição.
- Se 1.2 não for anunciada, serviço ausente, versão/método não suportado, registrar operação indisponível. Sem ensaio autenticado de getAllProperties. Uma indisponibilidade sem recusa final permite apenas fallback ONVIF já elegível por D03, nunca outro vendor.
- No plano VIEWER_SAFE público, 401 com challenge pode indicar exigência de autenticação, mas não autoriza replay: registrar HTTP_ERROR/status 401/auth NONE e “serviço exige autenticação; credencial não testada”. Sem challenge válido, registrar 401 sem inferir causa. Nenhum dos casos testa a senha. 403 público fecha acesso conforme ledger atual; TLS/cancelamento/deadline interrompem imediatamente.
- **Decisão Axis desta revisão: ANONYMOUS_ONLY_CONSERVATIVE.** A chamada é efetivamente anônima quando não envia credenciais/cookies/auth hooks e o equipamento a aceita. O nível documental Anonymous não promete que a interface esteja exposta naquele parque. Os exemplos genéricos com credenciais não comprovam um perfil Viewer autenticado específico. Não acrescentar esse perfil, nem ativá-lo no contrato TRANSPORT. Uma futura alternativa exige fonte oficial por operação e aplicabilidade, gate G-P0-AXIS-AUTH-EVIDENCE, aprovação normativa e execução separadas.
- Challenge versus recusa final é função do plano selecionado antes da primeira conexão: somente numa operação já autorizada para Digest, sem Authorization na primeira troca e com desafio suportado, cabe negociar na mesma tentativa lógica. O 401 após essa negociação é AUTH_REJECTED; 403/200+error 2001 fecham o escopo. Este esclarecimento preserva o handshake dos adapters existentes e não transforma o plano público Axis em autenticado. Sem troca de mecanismo, algoritmo, versão, família ou conta; todas as trocas físicas consomem budget.
- HTTP 200 com objeto error não é sucesso. Códigos Axis documentados 2003/2004 indicam versão/método indisponível; 2001 indica autorização negada, fecha o ledger mesmo em HTTP 200 e impede fallback autenticado. Outros erros são classificados sem persistir mensagem/body; não inventar códigos remotos.
- Preservar método Operator com escopo interno ELEVATED_AUTHORIZED, selecionado antes de I/O somente por perfil explicitamente autorizado, com suporte de versão e mecanismo existente. Nunca inferir privilégio de username “admin”, hint, 200 público ou recusa. Não criar seletor CLI/TOML de papel neste P0; caminho elevado permanece retido e exercitável em fixtures, mas a ativação operacional requer autoridade própria.
- Teto do novo plano público: duas operações físicas (versões + propriedades), sem login, redirects ou retry automático de POST. Versão já conhecida reduz para uma. Respeitar budget NATIVE 10s/global; erro na primeira não inicia a segunda.

**Interfaces:** plano interno tipado e imutável, limitado a esses dois escopos; nenhum novo campo em CameraResult ou motor genérico. Adicionar identificadores exatos das operações às allowlists/diagnósticos e cálculo de collection_method sem contar consulta de versão isolada como identidade. Parser só promove propriedades reconhecidas e válidas; P1-03 trata HardwareID.

### P0-02 — Panasonic Partial Collection

**Evidência:** filtro de `strategy.py:141–143,404` exclui Panasonic por não preencher toda identidade; parser `panasonic.py:207` fornece NAME/SERIAL/VERSION, sem fabricante explícito. A CGI `GET /cgi-bin/getinfo?FILE=1` é documentada como nível 3/Live only para famílias abrangidas. [i-PRO, §9.1 e níveis de acesso](https://i-pro.com/products_and_solutions/en/media/document/35381).

- Separar “fonte elegível para campos parciais” de “fonte que pode encerrar IDENTITY_V1”. Registro no registry não demonstra suporte, mas ausência de fabricante no payload não elimina modelo/serial/firmware válidos.
- Manter uma descrição interna explícita de suporte: família, operação, campos esperados e referência de modelo/família/firmware. Sem string-substring como prova de identidade, extensão bag ou framework.
- Somente executar a CGI quando um perfil documentado aplicável ao modelo/família estiver selecionado por informação existente permitida. O manual cita WV-S2531L; isso é referência documental, não homologação nem garantia de todos os firmwares. Nenhuma faixa de firmware deve ser inventada. Quando aplicabilidade for indeterminada ou Panasonic legado ambíguo, SKIPPED/ENDPOINT_UNSUPPORTED e diagnóstico “compatibilidade não comprovada”; não consultar get_capability ou outro endpoint para descobrir suporte.
- P0 entrega infraestrutura integrada de fonte parcial, catálogo restrito de aplicabilidade e interface interna tipada. Valida isoladamente seleção/skip, parser, merge, ledger, orçamento e projeção usando fixture pelo mesmo caminho canônico; a injeção de perfil no teste não cria seletor operacional oculto. O modelo CLI/XLSX é P1-01. Sem perfil documental suficiente ou modelo já observado utilizável com D03, entradas históricas continuam SKIPPED nesta fonte. PASS offline de P0 não significa Panasonic operacionalmente homologado.
- **Dependência acíclica:** P0-02 define a interface → P1-01 a alimenta → integração conjunta comprova o percurso de entrada até CGI e saída. P0 não depende da entrada P1 para seu aceite de infraestrutura; P1 depende da interface P0. Modelo declarado só seleciona perfil, nunca fecha identidade. Separar os fatos: aplicabilidade documental, disponibilidade real da operação e autorização da conta. Nenhum desses fatos prova automaticamente os outros.
- Com plano elegível, uma leitura GET lógica na família selecionada, Digest existente e budget corrente; handshake conta como trocas físicas, sem novo login lógico. Não autenticar apenas por firmware/MAC se fabricante/modelo/serial já estiverem completos. Resposta 200 válida prova apenas dados efetivamente retornados na combinação usada; 404 encerra como indisponível, 401 final/403 como recusa da conta/escopo. Não reconfigurar câmera nem diagnosticar ausência de API como papel Viewer insuficiente.
- Declarar Panasonic/i-PRO direciona a operação, mas não cria EvidenceRecord manufacturer. NAME é modelo, VERSION firmware, SERIAL serial; P1 acrescentará MAC. Dados ausentes permanecem None. Não transformar nome de equipamento em hostname.
- Campos parciais são mesclados antes de decidir complemento. ONVIF somente se essencial faltar e D03 permitir; rejeição/negação/TLS encerra. Fabricante forte já observado é preservado, sem sobrescrever conflitos.

### P0-03 — Viewer-only ACL Tests

Fixtures devem implementar matriz de autorização por operação e identidade de conta, separada do nome textual. Verificar a credencial sintética efetiva quando houver login; não aceitar qualquer Authorization presente como autenticação válida. Para Digest, verificar método/URI/challenge/response via biblioteca existente ou verificador limitado de fixture; sem criptografia de produção própria. Papéis Viewer, Operator e Admin recebem ACL distintas e não podem ser elevados por indicação do cliente.

A fixture pública não deve receber segredos. Mecanismos autorizados têm teste de challenge e final rejection. Permissões insuficientes não se “descobrem” pela tentativa de métodos elevados. Cobrir JSON erro em 200, 401, 403, 404/405, payload parcial e recursos ausentes. Reutilizar fixtures locais Requests/Zeep existentes; nenhuma câmera real. Regressão isolada por SINGLE/MULTI e por linha, inclusive IP duplicado, sem troca de credenciais/estado.

### P0-04 — Transport Provenance

Capturar o scheme efetivo já validado na borda de transporte e propagá-lo por tentativa/evidência, com valores HTTP ou HTTPS. URL só pode existir transitoriamente no cliente; persistir apenas o enum de scheme, nunca a URL. ONVIF continua como protocolo lógico ONVIF; scheme HTTP/HTTPS deve ir em metadado tipado/allowlisted já compatível com CollectionAttempt (ex.: chave scheme), sem mudar o significado do protocolo ou as colunas históricas.

Adapters não devem marcar falha TLS como “HTTP usado”: registrar HTTPS tentado/TLS_ERROR e zero operações posteriores. Se falhar antes da seleção de transporte, marcar transporte não executado/ausente, sem inventar HTTPS. Método lógico VENDOR_HTTP não comprova TLS. SINGLE exibe ONVIF (HTTP) ou ONVIF (HTTPS) quando houver scheme comprovado. Na coluna PROTOCOLO de DIAGNOSTICOS, representar ONVIF/HTTP ou ONVIF/HTTPS por allowlist fechada; manter ONVIF quando não houver transporte executado/comprovado. Isso não altera o protocolo lógico nem collection_method; é refinamento aprovado prospectivamente no gate G-P0-META. Para vendors, PROTOCOLO continua HTTP ou HTTPS. Layout de nove colunas preservado; não acrescentar URL ou coluna arbitrária.

### P0-05 — Baseline Traceability

Antes de qualquer implementação futura, confirmar raiz/branch/HEAD, status tracked/untracked restrito a paths governados e hashes de bytes locais relevantes; diferenciar SHA-256 de arquivo e blob Git. Inventariar delta preexistente, inclusive contratos R2/teste R2 não rastreados, sem adicionar tudo ao staging ou examinar segredos/planilhas privadas.

Comparar contra este manifesto, declarar divergência material e parar o escopo afetado. Não transplantar master, limpar, sobrescrever, resetar, restaurar, stash, criar branch, sincronizar ou publicar. Registrar quais arquivos já estavam modificados e quais o executor alterou. Validar integração contra o conteúdo sujo real e seus componentes reais, não somente contra HEAD, módulos fake ou número histórico de testes.

## 7. Critérios de aceite e matriz AC → teste → evidência futura

Todos os testes abaixo são **PREVISTOS / NOT_RUN** nesta autoria. IDs T-* são casos a criar/reutilizar com conteúdo verificado; não são alegação de função já existente. Evidência futura mínima por AC: ID, teste/função ou comando, baseline+hash do delta, resultado, contagens de requests/operações e trecho sanitizado da asserção. Não salvar body/header bruto como prova.

| AC único | Resultado verificável | Teste / método | Evidência futura |
|---|---|---|---|
| ASTRA-P0-01-AC01 | Viewer usa só versões + método irrestrito 1.2, nenhuma credencial/Operator | T-P0-AX01 transporte real de fixture e spy de auth | Ordem de até 2 POSTs públicos, logical_auth=0, campos válidos |
| ASTRA-P0-01-AC02 | Versão já obtida reutilizada; ausente/unsupported/malformed não enumera nem autentica | T-P0-AX02 parametrizado | Contagens por variante e ausência de getAllProperties |
| ASTRA-P0-01-AC03 | 200+error 2001, 401 público com/sem challenge e 403 não viram sucesso nem replay com senha | T-P0-AX03 ACL/JSON error parametrizado | Categoria correta, credencial não testada no 401 público e zero contorno |
| ASTRA-P0-01-AC04 | Operator retido só para escopo elevado explícito antes de I/O; username não o ativa | T-P0-AX04 Viewer/Operator/Admin | Matriz papel/plano/resultado e ausência de seletor implícito |
| ASTRA-P0-01-AC05 | TLS inválido, deadline/cancel ou body inseguro encerra plano público | T-P0-AX05 + testes transport existentes | Zero próximo POST/login, close verificado |
| ASTRA-P0-02-AC01 | Perfil Panasonic documentado em fixture canônica pode produzir parcial sem manufacturer, sem alegação operacional | T-P0-PN01 adapter real + contexto/transport fixture | Modelo/serial/firmware preservados; hint fora da evidência |
| ASTRA-P0-02-AC02 | Aplicabilidade desconhecida/legado não chama CGI; conflito forte não seleciona vendor | T-P0-PN02 variações de suporte/resolver | SKIPPED e zero requests nativas ou família alternativa |
| ASTRA-P0-02-AC03 | Parcial sobrevive a 403/401 final/TLS no complemento; nenhum login posterior | T-P0-PN03 cadeia integrada | PARTIAL_SUCCESS, tentativas/proveniência intactas, zero pós-falha |
| ASTRA-P0-02-AC04 | 404, vazio, XML/texto inválido e nomes semelhantes não fabricam identidade | T-P0-PN04 parser e estratégia | Campos ausentes e categoria correta, sem overwrite |
| ASTRA-P0-03-AC01 | ACL diferencia Viewer/Operator/Admin por operação e verifica credencial efetiva | T-P0-ACL01 servidor local | Mesmo payload sob papéis distintos produz autorização distinta |
| ASTRA-P0-03-AC02 | Challenge Digest conta fisicamente; 401 final/403 fecha scope | T-P0-ACL02 negociação | Ledger lógico/físico e zero auth posterior |
| ASTRA-P0-03-AC03 | SINGLE e MULTI usam as mesmas regras; IPs/linhas não compartilham sessão/credencial | T-P0-ACL03 entrypoint e lote concorrente | Ordem, sessões isoladas, sentinelas ausentes |
| ASTRA-P0-03-AC04 | 200 incompleto ≠ completo; hint/porta acessível não fecha identidade | T-P0-ACL04 projeção e saída | SUCCESS/PARTIAL_SUCCESS/FAILED/CANCELLED conforme §2 |
| ASTRA-P0-04-AC01 | HTTP autorizado é HTTP em tentativas/evidência/UI/XLSX | T-P0-TR01 integrado | Valores allowlisted e nenhuma URL/credencial em saídas |
| ASTRA-P0-04-AC02 | HTTPS confiável é HTTPS; TLS inválido encerra sem HTTP posterior | T-P0-TR02 TLS fixture | Categoria TLS e contagem HTTP pós-erro igual a zero |
| ASTRA-P0-04-AC03 | HTTP não autorizado, redirects e destinos/portas externos continuam negados | T-P0-TR03 regressão transporte | Negação antes de enviar; sem proxy/netrc |
| ASTRA-P0-05-AC01 | Executor comprova R2 local+delta e baseline divergente para antes de editar | T-P0-BL01 inventário/hash e caso de divergência | Manifesto local/delta e comando Git read-only |
| ASTRA-P0-05-AC02 | Sem perda de alterações preexistentes ou publicação; integração no fluxo real offline | T-P0-BL02 comparação pré/pós + suíte | Paths/hashes/diff explícitos; zero Git consequencial |
| ASTRA-P0-01-AC06 | Perfil público é fixado antes de I/O; configuração HTTP/Digest, username admin e challenge não ativam auth Axis ou Operator | T-P0-AX06 plano + ACL + TRANSPORT | logical_auth=0; até dois POSTs públicos; nenhuma mudança de plano |
| ASTRA-P0-02-AC05 | P0 isolado valida infraestrutura e SKIP produtivo sem modelo/perfil; não declara suporte operacional | T-P0-PN05 fluxo canônico com fixture e sem hint | Perfil interno restrito, ausência de seletor oculto e homologação NOT_VERIFIED |
| ASTRA-P0-02-AC06 | P0+P1 separa suporte, API e permissão para modelo exato, desconhecido, firmware incerto, 404, 401 final e 403 | T-P0-PN06 conjunto com T-P1-MH08 | Matriz por variante, contagens físicas/lógicas e parciais preservados; sem PASS físico |
| ASTRA-P0-G-AC01 | Todas AC locais e regressão acumulada passam; 14 campos e segurança preservados | T-P0-REG01 suíte integral Python 3.14/Windows | Resultados novos sem falha/skip/deselection; limites descritos |

## 8. Mudanças normativas e decisões para aprovação

| Gate | Proposta fechada para decisão do usuário | Relação com autoridade anterior |
|---|---|---|
| G-P0-AXIS | Autorizar prospectivamente dois métodos públicos Axis no mesmo CGI; versão 1.2 e plano de no máximo 2 operações | Delta das operações R2/P2, não reabertura de P1 histórico |
| G-P0-PARTIAL | Fonte parcialmente útil pode ser selecionada com suporte documentado, sem assumir identidade completa | Refinamento explícito R2 §3.1/3.2 e AC-03; preservar P2, D03 e conflitos |
| G-P0-META | Registrar scheme efetivo e novas operações allowlisted, sem campos CameraResult ou schema aberto | Refinamento de proveniência/diagnóstico; transporte e destinos não ampliados |
| G-P0-EXEC | Autorizar implementação offline deste contrato após aprovação e baseline pronta | Aprovação documental não é execução nem homologação |
| AUTH-EXT | DEFERRED: novos algoritmos Digest, HTTP Digest ONVIF ou Basic sobre TLS | Exige contrato separado por serviço/perfil, biblioteca compatível e autorização de risco. Não implementar neste P0/P1 |
| G-TR-NORM / G-TR-OPS | Aprovar o delta centralizado e, separadamente, uso real por conjunto fechado de IP/componente/porta com aceitação dos riscos HTTP | Detalhes no contrato TRANSPORT; este card não autoriza HTTP real |
| G-P0-AXIS-AUTH-EVIDENCE | DEFERRED: fundamentar eventual autenticação Viewer da mesma operação antes de propor outro perfil | Nenhum replay público→autenticado autorizado nesta revisão |

A direção técnica P0/P1 está APPROVED pelo novo Card; os deltas finais desta revisão permanecem PENDING_FINAL_NORMATIVE_APPROVAL. Se o usuário rejeitar um delta, a execução dependente fica bloqueada. F04 não é declarado resolvido pelos testes ACL.

## 9. Segurança, limitações e riscos

APIs públicas podem estar ausentes/desabilitadas; não habilitá-las. Conta viewer e método público não garantem propriedades completas. Dados em HTTP não são confidenciais por usar Digest. Credencial de mídia/web pode não existir em ONVIF. Aplicabilidade Panasonic não comprovada limita coleta em entradas históricas sem modelo. Timeout permanece soft durante chamadas bloqueadas. Leitura pode gerar logs/sessões incidentais no equipamento; nenhuma alteração de configuração é permitida.

## 10. Dependências, sequência e roteamento futuro

Sequência mínima: aprovar deltas finais e definir interfaces do TRANSPORT → P0-05 preflight → aprovar interfaces/ledger público e proveniência (P0-04) → integrar Axis (P0-01) → fonte parcial Panasonic (P0-02) → ACL transversal (P0-03), começando fixtures antes de seus respectivos deltas → regressão e revisão. Testes acompanham cada slice e integração SINGLE/MULTI; não acumular módulos isolados até o final.

DIRECT é recomendado: seleção, ledger e diagnóstico compartilham arquivos e contratos. Multiagente futuro somente se separar uma frente realmente independente (ex.: testes sem edição de produção) trouxer ganho material e houver autorização; não é requisito para fechar P0. Política canônica: `../governanca_de_projetos/Matriz Unificada de Políticas/policies/AGENTS-Multiagente-Generico-v1.7-R2.3-Roteamento-Economico.md`. Nenhum subagente foi usado nesta autoria.

## 11. Gates, evidências de conclusão e condições de parada

G0 aprovação dos deltas + autorização offline; G1 baseline/support/ownership; G2 módulo e integração em fluxo canônico; G3 regressão acumulada; G4 revisão técnica/security focal da mudança de auth pública/proveniência; G5 continuidade e aceite da entrega. Homologação física/publicação/build são gates separados e NOT_AUTHORIZED.

Parar diante de: baseline alterada sem explicação, documentação insuficiente para suporte selecionado, necessidade de novo endpoint/mecanismo, auth final/403/TLS, expansão de escrita, dependência ausente, falha de segurança/regressão, impossibilidade de executar suíte integral ou ambiguidade contratual. Não relaxar controles ou esconder skips para passar gates. Reabertura de testes só por nova mudança/falha justificada.

## 12. Reversibilidade e rollback

Delta pequeno, sem migração persistente ou alteração em câmera. Preservar inventário de bytes e diff por path. Para rejeitar implementação futura, primeiro interromper a execução; preparar patch inverso apenas dos hunks do executor e revisar alterações concorrentes. Aplicar reversão somente com autorização específica; nunca reset/restore/clean/stash ou sobrescrever worktree. Pode-se permanecer na baseline pré-delta, declarando suas limitações; não tornar método Operator o fallback de Viewer nem remover o bloqueio TLS/RTSP.

## 13. Definition of DONE

Implementação futura só DONE após G0–G5 e ASTRA-P0-G-AC01, todos os AC da seção 7 com evidência nova, SINGLE/MULTI integrados, segurança/dados/budgets/14 campos preservados e nenhuma alteração de equipamento ou artefato não autorizado. Sucesso offline não significa viewer homologado em hardware, autorização de P1, publicação ou fechamento das fases históricas.

Autoria deste documento é READY_FOR_FINAL_NORMATIVE_APPROVAL quando tem escopo, valores propostos, AC/testes, conflitos, baseline e gates rastreáveis. TEST_EXECUTION=NOT_REQUIRED nesta autoria. PROJECT_STATE e o gate de handoff real determinam fechamento formal, separadamente da qualidade dos contratos.

## 14. Matriz F01–F09 → contratos e disposições

Nenhum finding é CLEARED por este plano. Referências de código são as observadas pela auditoria original, recuperadas sem novo diagnóstico.

| Finding original | Fato/evidência recuperada | Destino | Disposição/limite |
|---|---|---|---|
| F01 HIGH | Axis getAllProperties Operator; axis.py:35 e strategy.py:216 | P0-01/P0-03 | Correção proposta de menor privilégio; validação física futura |
| F02 HIGH | Panasonic excluído por identity completeness; strategy.py:141/404 | P0-02; P1-01 integração com modelo | Refinar R2; parcial não inventa fabricante |
| F03 HIGH | Fixtures sem ACL e AC-19 diferido; test_hikvision_isapi.py:66 | P0-03 + gate de homologação | ACL offline não resolve prova operacional |
| F04 MEDIUM | ONVIF WSSE fixo, Digest nativo limitado; transport.py:573; hikvision.py:220 | P0-03 testes de limite; AUTH-EXT | Expansão de auth DEFERRED fora destes contratos |
| F05 MEDIUM | Entrada sem model_hint e apenas IP literal; inventory_service.py:188; ui.py:36 | [P1-01](ASTRA_P1_COVERAGE_IMPROVEMENTS_IMPLEMENTATION_CONTRACT.md) | Modelo proposto; hostname de entrada OUT pelo requisito IP deste Card |
| F06 MEDIUM | HardwareId/HardwareID/MAC ignorados; onvif/adapter.py:118; axis.py:162; panasonic.py:207 | P1-03 | Mapear respostas existentes; hostname e novas leituras de rede OUT |
| F07 MEDIUM | RTSP disabled e snapshot limitado a KD8003; snapshot/rtsp.py:29 | [P2 diferido](ASTRA_P2_MEDIA_DEFERRED_DECISION_RECORD.md) | Bloqueio preservado, sem contrato executável |
| F08 MEDIUM | Scheme HTTPS fixo; axis.py:114; transport.py:379 | P0-04; P1-02 diagnóstico | Duração MULTI zero observada é backlog separado, não corrigida implicitamente |
| F09 MEDIUM | R2 sujo posterior ao publicado | P0-05 | Rastreabilidade local; Git/publicação continuam exigindo autorização |

## 15. Próximo passo e status

A direção técnica foi aprovada; o usuário deve apreciar os deltas normativos finais e, em decisão separada identificável, autorizar implementação offline se desejar. P1 depende dos gates relevantes deste P0 conforme seu próprio contrato. Até lá: CONTRACT_STATUS=READY_FOR_FINAL_NORMATIVE_APPROVAL; IMPLEMENTATION_APPROVAL=NOT_GRANTED; VIEWER_REAL_COMPATIBILITY=NOT_VERIFIED. Não executar este documento como consequência de sua criação.

## 16. Adendo final 02 — rastreabilidade e dependências

Esta revisão substitui a proposta V1 deste arquivo, SHA-256 `6a9d89726e7e192be710c85e1ba1bc0a11079738a206dae7bbd98f71c9bd5cbe`. A V1 era proposta, sem autoridade de implementação. IDs anteriores são conservados; foram acrescentados AX06, PN05 e PN06. O texto das seções acima já incorpora a nova redação; esta tabela explica cada delta material.

| Delta / justificativa | Regra afetada → nova redação vigente | AC / teste | Evidência futura | Dependência | Aprovação requerida |
|---|---|---|---|---|---|
| A1: evitar confundir CGI autenticável com Viewer comprovado | P0-01/§5 → plano público fixo; 401 não habilita credencial; eventual Viewer autenticado diferido por evidência insuficiente | AX01–03/06; T-P0-AX01–03/06 | Ordem, ausência de Authorization e logical_auth=0 | Fonte oficial específica para eventual exceção | G-P0-AXIS; exceção somente G-P0-AXIS-AUTH-EVIDENCE futuro |
| A2: preservar D03 sem proibir handshake legítimo em outras operações | §5/P0-03 → negociação só no mecanismo já selecionado; 401 final/403/2001 fecham ledger | ACL02/AX03; T-P0-ACL02/AX03 | Transições e trocas físicas/lógicas; zero auth posterior | Ledger PRE-P12 atual | D03 sem ampliação; G-P0-EXEC |
| B1: eliminar dependência circular P0/P1 | P0-02/DoD → infraestrutura P0 aceita isoladamente; operação por modelo na entrada depende de P1 e gate conjunto | PN01/05/06; T-P0-PN01/05/06 | Fixtures no fluxo real e matriz de disponibilidade/conta | P0 interface → P1 ModelHint → G-PN-JOINT | G-P0-PARTIAL; G-PN-JOINT |
| C1: centralizar política sem duplicar transporte | §3/5/8/10 → grupo fechado compilado em TransportRule exata; seleção pré-I/O e proveniência, sem autorização HTTP real | TR01–03 e ASTRA-TR-AC01–15 | Plano congelado/contagens/saídas sanitizadas | Contrato TRANSPORT e P0-04 | G-TR-NORM, G-TR-IMPL; G-TR-OPS separado |
| S1: registrar aprovação de direção, mantendo deltas pendentes | Cabeçalho/§8/13/15 → direção aprovada ≠ deltas finais ≠ execução | G-AC01; revisão documental | Estado coerente e arquivos preservados | Card final 02 | Aprovação final do usuário; sem gate de execução presumido |

A matriz canônica de dependências, critérios conjuntos Panasonic, sequência mínima e lista de reconciliação estão nas §§8–12 do [TRANSPORT](ASTRA_CENTRALIZED_TRANSPORT_IMPLEMENTATION_CONTRACT.md). O [P2](ASTRA_P2_MEDIA_DEFERRED_DECISION_RECORD.md) permanece DEFERRED e byte a byte preservado. O relatório documental não concede CLEARED a F01–F09.
