# Contrato P2 — Expansão da estratégia de coleta

## Metadados e classificação

- Atividade: P2-A01
- Tipo: contrato arquitetural aprovado; sem implementação
- Direção P2 aprovada: `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`
- Estado do contrato: `APPROVED` (aprovação humana registrada em 2026-10-09)
- Implementação P2: `NOT_GRANTED`
- Estado P0/P1: encerrados. O contrato P1 permanece histórico e válido, inclusive `VENDOR_FIRST_WHEN_KNOWN`; este documento não o reabre nem o altera.
- Autoridade: usuário. D00–D06 estão aprovadas conforme reconciliação de 2026-10-09; D07 permanece diferida. A aprovação contratual não encerra P2 nem autoriza implementação.

Este contrato traduz a direção aprovada em requisitos verificáveis para uma futura decisão de implementação. A auditoria arquitetural é a fonte de evidências e deve ser consultada para o diagnóstico completo: `docs/audit/ARCH_AUDIT_01_REPORT.md`. O documento não substitui o estado do projeto nem os planos canônicos.

## 1. Objetivo, escopo e limites

Preservar o monólito modular Python, controller e workflows existentes, separação entre domínio, coleta e apresentação, credenciais individuais por câmera, modo `READ_ONLY`, ONVIF genérico, adapters nativos por fabricante e resultados parciais. O fluxo `SINGLE` continua canônico e passa a selecionar coleta de forma híbrida e determinística.

Este contrato não redesenha o produto, não implementa `MULTI` ou concorrência, não consulta câmeras reais nem credenciais e não concede autorização de implementação. Não altera o contrato P1, os 14 campos históricos de `CameraResult`, a continuidade ou o roadmap P3–P12. Extensões futuras devem ser incrementais e aprovadas.

## 2. Evidência arquitetural relevante

O baseline observado pela auditoria e confirmado para esta atividade indica que `main.py` compõe `InventoryService(VendorFirstCollector)`, `SingleWorkflow` e `ApplicationController`. `CameraResult` contém 14 campos sem senha; `CameraTarget` contém IP, usuário e senha, com a senha protegida de `repr`. O coletor atual exige preauth, resolve fabricante sem hint e usa registry com fallback/complemento ONVIF. Fingerprinting busca substring e usa a primeira ocorrência. O registry permite adapters arbitrários e substituição de duplicatas; adapters de fabricante são placeholders não registrados. `InventoryService` converte exceptions em falha sem reter evidência interna e não há diagnóstico por tentativa/etapa.

### Findings que o contrato precisa resolver

- **F01 — perda de evidência:** falhas tardias podem apagar dados anteriormente válidos; exception e `AdapterResult.FAILED` têm semântica distinta.
- **F02 — resolução instável:** substring pode produzir falso positivo e a ordem do payload pode alterar fabricante selecionado.
- **F03 — diagnóstico insuficiente:** faltam tentativas e resultados por etapa, operação e protocolo.

## 3. Princípios e invariantes

1. **READ_ONLY:** permitir apenas operações de leitura explicitamente autorizadas. Métodos SOAP `POST` só são permitidos quando a operação de leitura estiver em allowlist. Bloquear `Set*`, reboot e alterações de configuração, usuário, senha, horário ou rede.
2. **NO_PASSWORD_OUTPUT:** senha e credenciais não aparecem em resultado, logs, exceções, UI, Excel, URL ou `repr`; nunca guardar headers, corpos, URL ou exception brutos em diagnósticos.
3. **NO_CREDENTIAL_SPRAYING:** no máximo duas tentativas autenticadas lógicas por dispositivo: primária e uma secundária elegível somente se faltar fabricante confirmado, modelo ou serial number. Nenhuma autenticação em APIs de vários fabricantes. Negociação HTTP Digest challenge pertence à mesma tentativa lógica.
4. **PER_TARGET_CREDENTIAL_SCOPE:** usar somente a credencial do `CameraTarget`/linha. Sessão e credenciais só podem ser reutilizadas para o mesmo alvo e escopo e devem ser fechadas ao final.
5. **NO_UNAUTHORIZED_REDIRECT / NO_INSECURE_TLS_DOWNGRADE:** destino, scheme e porta precisam estar explicitamente permitidos e ligados ao alvo. Bloquear cross-origin, userinfo, credenciais em URL e downgrade TLS. HTTPS valida certificado; certificado não confiável falha sem fallback inseguro.
6. **Evidência monotônica:** evidência válida é registrada assim que validada e nunca removida por exception, timeout, retorno `FAILED`, rejeição de autenticação, falha de fallback, cancelamento ou erro inesperado.
7. **Proveniência explícita:** cada valor coletado mantém sua fonte e operação. Valores vazios, placeholders ou inválidos não substituem evidência válida; merge não usa last-write-wins.
8. **Semântica honesta:** descoberta parcial não equivale a inventário autenticado. Fabricante descoberto não prova identidade completa.

### Transporte e limites de segurança

Por câmera, conexões ficam restritas aos destinos e portas explicitamente autorizados; portas podem diferir por protocolo. XAddr e redirects devem permanecer no destino permitido associado ao alvo, conforme política explícita de scheme/host/porta, sem userinfo; redirecionamentos não autorizados são bloqueados. Não usar `verify=False`, `trust_env` ou autenticação implícita via proxy/netrc. Respostas e corpos têm limites de tamanho; XML é analisado com parser seguro, sem entidades externas; sessões são fechadas. HTTPS valida certificado; CA interna ou pinning só quando explicitamente configurado. HTTP só é permitido quando explicitamente configurado para o alvo; nunca degradar automaticamente HTTPS para HTTP. Endereço do alvo e autenticação nunca vazam para logs, exceptions, UI, Excel ou representação de objetos.

## 4. Estratégia híbrida determinística

A seleção considera fabricante `DECLARED`, `OBSERVED` e `RESOLVED`, evidência estruturada, adapter funcional e habilitado, operações suportadas, os três campos essenciais de identidade e suas lacunas, evidência já obtida, mecanismo e escopo de autenticação, budgets, deadline e cancelamento. Um hint declarado orienta roteamento, mas não confirma fabricante.

- Com hint confiável e adapter funcional que suporte os campos, não executar preauth ONVIF obrigatório.
- Com fabricante desconhecido, fazer descoberta anônima curta e limitada, reutilizada na seleção; depois escolher coletor genérico ONVIF se utilizável.
- Preferir adapter nativo somente quando evidência/capability justificarem a escolha. Um placeholder não é adapter habilitado.
- Não criar motor genérico de regras, não autenticar APIs de vários fabricantes e não duplicar consulta apenas para obter duas fontes.
- Uma segunda fonte autenticada só é elegível se ainda faltar fabricante confirmado, modelo ou serial number e se D03 permitir; dados complementares não iniciam autenticação adicional. Orçamento e deadline também precisam permitir a leitura.
- Budget inicial aprovado: no máximo duas tentativas autenticadas lógicas por câmera, primária e secundária elegível, cada qual no máximo uma vez. A secundária só é elegível se ainda faltar fabricante confirmado, modelo ou serial number, a primeira não tiver terminado em rejeição final nem autorização negada, e o orçamento permitir. Challenge HTTP Digest faz parte da tentativa e não é retry. Exceções não podem ultrapassar esse limite sem nova aprovação.
- Após rejeição final ou autorização negada, não iniciar nova autenticação automática no dispositivo. Reutilizar sessão aceita somente no mesmo alvo/escopo e até a primeira recusa. Não trocar de fabricante nem repetir a autenticação rejeitada.
- `PREAUTH=PASS`, fabricante Hikvision e ONVIF `TIMEOUT` preservam o fabricante e a descoberta parcial; não classificam o resultado como inventário autenticado.

### Orçamento e retry

Budgets cumulativos de referência: `CONNECT_TIMEOUT=3s`; `READ_TIMEOUT=7s`; `ONVIF_BUDGET=15s`; `NATIVE_BUDGET=10s`; `CAMERA_SOFT_DEADLINE=45s`. Cada operação usa o menor valor entre seu timeout, o restante do budget da fonte e o tempo restante. Não iniciar operação após deadline ou cancelamento. Respostas são limitadas. Retry só para leitura idempotente transitória e com budget: no máximo um retry de aplicação por operação, com backoff de 1 s, quando a política permitir. Excluir rejeição de autenticação, autorização negada, entrada inválida, TLS, conexão recusada, operação não suportada e resposta deterministicamente inválida. Handshake Digest oculto não é retry de aplicação. Deadline soft e cancelamento não podem prometer interromper threads já bloqueadas.

O plano também impõe um limite cumulativo de requests: contar cada troca HTTP/SOAP real, inclusive challenge/response Digest, redirects permitidos, descoberta interna do cliente e retry. A negociação Digest conta como uma autenticação lógica, mas seus requests entram na contagem de transporte. Para descoberta, no máximo uma leitura `GetCapabilities`; `GetSystemDateAndTime` só quando necessário ao diagnóstico WS-Security. Cada fonte selecionada executa somente as operações previstas para os campos requeridos; a secundária executa no máximo uma operação de complemento. Não permitir retries/descobertas ocultos sem orçamento nem repetir capabilities já obtidas. O limite efetivo é a soma finita do plano escolhido e de retries elegíveis, encerrando assim que a cobertura requerida for atingida.

## 5. Resolução de fabricante e conflitos

Manter separados fabricante `DECLARED`, `OBSERVED` e `RESOLVED`. Preservar hint declarado literalmente e também sua forma normalizada. Confiança: `STRONG`, `WEAK`, `CONFLICTING` ou `UNKNOWN`; não produzir score probabilístico. Hint orienta roteamento e nunca equivale automaticamente a fabricante confirmado.

- Evidência estruturada com namespace exato, chave/modelo ou alias OEM documentado e testado pode ser forte conforme fonte e contexto.
- Identidade autenticada explícita é sinal forte; ainda assim, sinais fortes incompatíveis resultam em conflito, não em escolha pelo primeiro retorno.
- Namespace exato, identidade estruturada e XAddr só contam conforme serviço/contexto e destino validado; XAddr também passa pelos limites de destino da seção 3.
- `Server`, realm, OUI de MAC, substring e `deviceName` são no máximo sinais fracos.
- Nunca selecionar fabricante por substring arbitrária, ordem de rede ou primeiro resultado.
- Evidência forte observada divergente do hint preserva a divergência; a evidência forte é referência para resolução, sem autenticação adicional não permitida por D03. Duas evidências fortes conflitantes bloqueiam seleção automática de vendor; não escolher pela ordem ou pelo hint. ONVIF genérico só é elegível quando seguro e permitido pelo plano. Hint discordante de sinal fraco permanece hint e gera warning.
- OEM/rebranding requer alias documentado e testado.

Casos de aceite para o resolver: hint igual ao fingerprint; hint divergente; duas evidências fortes divergentes; somente sinal fraco; nenhum sinal; inversão da ordem das respostas; OEM/rebranding. Fabricante resolvido deve ser idêntico independentemente da ordem de chegada.

## 6. Autenticação e semântica de falhas

HTTP Digest e WS-Security UsernameToken são mecanismos diferentes. Selecionar explicitamente uma modalidade por tentativa. Challenge inicial/401 de negociação não é rejeição final; 401 final resulta em `AUTH_REJECTED`, sem afirmar que a senha está errada. 403 é `AUTHORIZATION_DENIED`, preservando semântica do dispositivo. SOAP `NotAuthorized` mantém incerteza; mecanismo não suportado é categoria distinta. Clock skew só pode ser considerado para WS-Security se houver evidência; leitura de hora nunca ajusta relógio. Root cause de Digest permanece `UNDETERMINED`; não declarar Digest corrigido.

Reutilizar sessão apenas no mesmo alvo/escopo; leituras na sessão aceita são permitidas até a primeira recusa. Após rejeição final ou autorização negada, interromper autenticação automática. Exceções a isso exigem prova de domínio de credencial independente e contrato/aprovação separados; a entrada atual não define credencial ONVIF separada. Não testar contra câmera real nesta atividade.

## 7. Diagnóstico e modelo de domínio proposto

Preservar compatibilidade histórica dos 14 campos P1 de `CameraResult`, sem adicionar um conjunto aberto de strings. Introduzir inicialmente somente `CollectionAttempt`, `EvidenceRecord` e `CollectionReport`; `CollectionReport` é a fonte de verdade agregada durante a coleta. `CameraResult` mantém os 14 campos P1 e recebe status calculado conforme `IDENTITY_V1`. Outros tipos apenas diante de necessidade demonstrada. Não introduzir persistência nem banco de dados. Nenhum segredo em modelo, serialização ou representação.

Cada `EvidenceRecord` contém valor validado, campo, fonte/protocolo/operação, confiança e instante. `CollectionAttempt`, um por operação, registra protocolo, operação, etapa, outcome, duração, status HTTP, código SOAP/vendor sanitizado, mecanismo de autenticação, erro normalizado e `retry_count`. Etapas mínimas: `DISCOVERY`, `CONNECT`, `HTTP`, `AUTH`, `SOAP`, `PARSE` e `MERGE`. Não armazenar header, body, URL ou exception brutos.

Contratos considerados para a evolução: `ScanRequest` transporta target, hint opcional, campos requeridos e identidade de linha quando houver lote; `AdapterSupport` declara fabricante, operações e campos realmente suportados; `AdapterResult` retorna evidências e tentativas por fonte sem substituir o relatório agregado. `NetworkInventory` fica para expansão incremental com estruturas concretas. Estado de protocolo não deve confundir serviço alcançável (`REACHABLE`/`UNREACHABLE`/`UNTESTED`) com autenticação (`AUTHENTICATED`/`REJECTED`/`UNTESTED`); essa dimensão só deve ser persistida em tipo explícito quando o perfil P2 aprovado exigir, nunca inferida de uma porta configurada.

O modelo deve distinguir `hostname` de `deviceName`, `hardware_id` de `hardwareVersion`, porta configurada de porta testada, hint de fabricante de fabricante observado, e ONVIF alcançável de ONVIF autenticado. Campos de rede reportados pertencem ao inventário de interface, não substituem o IP alvo. Fingerprint isolado não equivale a inventário completo.

Classes normalizadas: `CONNECT_TIMEOUT`, `READ_TIMEOUT`, `TLS_ERROR`, `AUTH_REJECTED`, `AUTHORIZATION_DENIED`, `AUTH_MECHANISM_UNSUPPORTED`, `ENDPOINT_UNSUPPORTED`, `SOAP_FAULT`, `INVALID_RESPONSE`, `DEADLINE_EXCEEDED` e `UNEXPECTED`; conexão recusada pode ter categoria própria se clara. Manter compatibilidade pública agregando em famílias do `ErrorCode` existente, sem expansão indiscriminada.

Exception e retorno `FAILED` equivalentes devem agregar status e dados coerentes. Mensagem ao operador identifica evidência coletada, operação que falhou e campos ausentes, sem segredos.

### Merge e status final

O merger é determinístico e por campo; não existe superioridade universal `native > ONVIF`. Comparar proveniência, explicitar conflito e aplicar apenas precedência específica justificada. Não substituir valor válido por vazio, placeholder ou valor inválido. Para `IDENTITY_V1`, conflito material nos campos essenciais de identidade impede `SUCCESS`; divergências apenas em campos complementares são preservadas e reportadas, mas não invalidam por si sós a identidade. Firmware, MAC, hostname, rede, protocolos e demais dados válidos disponíveis são complementares. Firmware ausente não impede `SUCCESS`. `SUCCESS` representa o perfil de identidade, não o inventário técnico completo.

- `SUCCESS`: em `IDENTITY_V1`, fabricante confirmado, modelo e serial number são válidos e não há conflito material; firmware ausente não impede esse status.
- `PARTIAL_SUCCESS`: há evidência útil, mas faltam campos ou existe conflito material.
- `FAILED`: nenhuma evidência útil.
- `CANCELLED`: status cancelado, mantendo evidência já coletada.

Relatório final distingue status, cobertura, proveniência, tentativas, conflitos, campos ausentes/não suportados e método de coleta. Um conflito em campo requerido impede sucesso pleno. Descoberta parcial não é inventário autenticado.

## 8. Decisões e aprovações

As decisões abaixo registram os requisitos contratuais aprovados; não são decisões de implementação. A aprovação do contrato não concede autorização para implementação.

### D00 — Direção arquitetural após P1

- **PROBLEM:** selecionar a direção para expansão após a slice SINGLE encerrada.
- **EVIDENCE:** ARCH-ALIGN-01 aprovou a direção híbrida; auditoria independente recomenda preferência nativa condicionada a fabricante, capacidade, campos, credenciais e orçamento.
- **ALTERNATIVES:** ONVIF-first universal; vendor-first fixo; política híbrida orientada a capacidade.
- **RECOMMENDATION:** `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`, mantendo monólito modular, P1 e ONVIF genérico.
- **RATIONALE:** evita descoberta/auth obrigatórios quando um caminho nativo comprovado cobre o perfil e preserva ONVIF como fonte comum, fallback ou complemento.
- **INVARIANTS:** P1 permanece `CLOSED`; sem redesign; sem login em todos os vendors; P2 implementation não autorizada.
- **CONTRACT_REQUIREMENTS:** seleção determinística e explicável, sem engine genérico de regras.
- **TEST_CRITERIA:** mesma entrada/evidências/capabilities produz o mesmo plano; não inicia operação após cobertura, deadline ou cancelamento.
- **APPROVAL_STATUS:** `APPROVED` (direção já autorizada em ARCH-ALIGN-01; não aprova decisões D01–D06).

### D01 — Perfil mínimo de identidade

- **PROBLEM:** definir cobertura mínima de identidade para classificar sucesso.
- **EVIDENCE:** a identidade mínima precisa ser distinguida da completude do inventário.
- **ALTERNATIVES:** firmware obrigatório; perfil menor; perfil versionado com fabricante, modelo e serial essenciais.
- **DECISION:** `IDENTITY_V1` exige fabricante confirmado por evidência estruturada e verificável, modelo e serial number. Firmware, MAC, hostname, rede, protocolos e demais dados válidos disponíveis são complementares. Fabricante declarado/hint isolado não é fabricante confirmado. `SUCCESS` exige os três campos essenciais válidos e ausência de conflito material nos campos essenciais; firmware ausente não impede sucesso. `SUCCESS` não afirma inventário técnico completo.
- **RATIONALE:** estabelece identidade mínima verificável sem confundi-la com completude do inventário.
- **INVARIANTS:** opcionalidade dos três campos essenciais somente por exceção explícita, justificada, versionada e aprovada futuramente; preservar compatibilidade histórica P1.
- **CONTRACT_REQUIREMENTS:** perfil nomeado `IDENTITY_V1`; firmware explicitamente complementar; status calculado pelo relatório agregado.
- **TEST_CRITERIA:** cada essencial ausente/inválido, fabricante apenas declarado, firmware ausente, conflito material e três essenciais válidos.
- **APPROVAL_STATUS:** `APPROVED_WITH_REVISION` (usuário, 2026-10-09).

### D02 — Domínio e relatório de coleta

- **PROBLEM:** representar tentativas, evidências e cobertura sem quebrar o contrato P1.
- **EVIDENCE:** `CameraResult` possui 14 campos históricos; falhas atuais não preservam evidência interna.
- **ALTERNATIVES:** ampliar diretamente `CameraResult`; criar modelos tipados auxiliares mínimos; adicionar coleção aberta de strings.
- **DECISION:** introduzir inicialmente somente `CollectionAttempt`, `EvidenceRecord` e `CollectionReport`. `CollectionReport` é a fonte de verdade agregada durante a coleta; `CameraResult` preserva compatibilidade com os 14 campos P1 e seu status é calculado conforme `IDENTITY_V1`. Não introduzir persistência nem banco de dados. Outros tipos somente diante de necessidade demonstrada.
- **RATIONALE:** preservar compatibilidade e viabilizar proveniência, tentativas e parciais.
- **INVARIANTS:** sem segredos; sem bag aberta; não alterar P1 neste documento.
- **CONTRACT_REQUIREMENTS:** status/coverage/provenance separados; evidência monotônica; revisão de versão em futura implementação.
- **TEST_CRITERIA:** serialização compatível; ausência de segredos; evidência preservada após falha e cancelamento.
- **APPROVAL_STATUS:** `APPROVED_WITH_ADJUSTMENTS` (usuário, 2026-10-09).

### D03 — Autenticação e fallback

- **PROBLEM:** evitar login automático repetido e definir quando outra fonte pode recuperar cobertura.
- **EVIDENCE:** entrada atual oferece credencial por alvo; Digest e WS-Security são distintos; seleção atual inclui preauth obrigatório.
- **ALTERNATIVES:** tentar ambos os protocolos sem limite; parar após qualquer tentativa autenticada; limitar a um caminho primário e uma complementação autenticada, interrompendo sempre após rejeição final.
- **RECOMMENDATION:** limitar a duas tentativas autenticadas lógicas por câmera: primária e uma secundária somente se ainda faltar fabricante confirmado, modelo ou serial, sem rejeição final ou autorização negada e dentro do budget. Uma família nativa por alvo.
- **RATIONALE:** reduz risco de spraying e mantém recuperação delimitada.
- **INVARIANTS:** `NO_CREDENTIAL_SPRAYING`, `PER_TARGET_CREDENTIAL_SCOPE`; no máximo duas tentativas lógicas autenticadas por dispositivo, sem repetição por fonte; handshake Digest não conta como retry.
- **CONTRACT_REQUIREMENTS:** classes de auth distintas; qualquer exceção ao budget requer domínio de credencial independente e aprovação própria. Requisições de leitura adicionais podem reutilizar a sessão aceita do mesmo escopo até primeira recusa.
- **TEST_CRITERIA:** rejeição final ou autorização negada interrompe auth; sem falta de fabricante/modelo/serial não há segunda autenticação; com lacuna elegível, no máximo uma secundária; tentativa em API de outro fabricante proibida; dados complementares não iniciam nova auth.
- **DECISION:** no máximo duas tentativas autenticadas lógicas por câmera (primária e secundária elegível). Fallback autenticado somente se faltar fabricante, modelo ou serial; interromper novas autenticações automáticas após rejeição final ou autorização negada. Distinguir challenge Digest de rejeição final. Não experimentar APIs de vários fabricantes. Credenciais individuais e isoladas por câmera. Dados complementares podem ser lidos em sessão já autorizada, dentro das operações e budgets permitidos, sem autenticação adicional somente para obtê-los. Causa raiz de ONVIF Digest permanece indeterminada.
- **APPROVAL_STATUS:** `APPROVED_WITH_ADJUSTMENTS` (usuário, 2026-10-09).

### D04 — TLS e destinos

- **PROBLEM:** delimitar redirects, XAddr, autenticação ambiente e confiança TLS.
- **EVIDENCE:** origem de XAddr/redirect pode expandir destino; configuração ambiente pode incluir proxy/netrc; downgrade após falha TLS seria inseguro.
- **ALTERNATIVES:** confiar livremente em URLs anunciadas; permitir mesma origem apenas; exigir destino explicitamente permitido e ligado ao alvo.
- **DECISION:** restringir conexões aos destinos e portas explicitamente autorizados por câmera; portas podem diferir por protocolo. Bloquear redirecionamentos não autorizados, `trust_env` e credenciais ambientais. HTTPS exige validação de certificado; admitir CA interna ou pinning explicitamente configurado quando necessário. HTTP só quando configurado explicitamente para o alvo; nunca degradar HTTPS para HTTP automaticamente.
- **RATIONALE:** restringe autenticação e tráfego ao escopo do dispositivo configurado.
- **INVARIANTS:** `NO_UNAUTHORIZED_REDIRECT`, `NO_INSECURE_TLS_DOWNGRADE`; nunca `verify=False` global; `trust_env` desabilitado.
- **CONTRACT_REQUIREMENTS:** allowlist explícita de destino; limites de payload; fechar sessão.
- **TEST_CRITERIA:** redirect cross-origin, XAddr divergente, userinfo, cert inválido e auth ambiente devem ser bloqueados conforme política.
- **APPROVAL_STATUS:** `APPROVED_WITH_ADJUSTMENTS` (usuário, 2026-10-09).

### D05 — PoC Hikvision ISAPI

- **PROBLEM:** definir primeiro adapter nativo limitado e testável.
- **EVIDENCE:** adapters atuais são placeholders não registrados; não há PoC funcional comprovado.
- **ALTERNATIVES:** ampliar ISAPI; implementar suíte P7 inteira; PoC de leitura mínima com fixtures.
- **DECISION:** PoC mínima Hikvision: `GET /ISAPI/System/deviceInfo`, HTTP Digest e XML seguro; integrar com adapter funcional, registry, diagnósticos, evidências e fluxo `SINGLE`. Priorizar fabricante, modelo e serial number; firmware e MAC são complementares. HTTP 200 sem conteúdo válido não é sucesso. Testes primeiro com fixtures; câmera real exige autorização operacional separada. Não antecipar implementação completa P7.
- **RATIONALE:** escopo estreito exercita adapter, registro e parcial sem alegar suporte abrangente.
- **INVARIANTS:** somente leitura, sem câmera real nesta atividade, sem sucesso em payload inválido, diagnósticos por etapa.
- **CONTRACT_REQUIREMENTS:** status de resposta do fabricante validado mesmo em HTTP 200; registro funcional com support declarativo; integração `SINGLE`; fixtures determinísticas.
- **TEST_CRITERIA:** parsing namespace, campos opcionais, erro de fabricante em HTTP 200, resposta inválida, auth Digest fixture, registry e integração.
- **APPROVAL_STATUS:** `APPROVED_WITH_ADJUSTMENTS` (usuário, 2026-10-09); implementação e teste operacional fora desta atividade.

### D06 — Fingerprint, conflitos e proveniência

- **PROBLEM:** resolver fabricante sem falso positivo nem dependência da ordem.
- **EVIDENCE:** implementação atual procura substring e escolhe primeira ocorrência; OEM pode divergir do hint.
- **ALTERNATIVES:** manter substring; resolver por score; regras estruturadas explícitas com conflitos preservados.
- **DECISION:** separar `DECLARED`, `OBSERVED` e `RESOLVED`; usar `STRONG`, `WEAK`, `CONFLICTING` e `UNKNOWN`. Hint orienta roteamento, não confirma identidade. Priorizar evidências estruturadas e verificáveis; não usar substring arbitrária nem ordem de chegada. Evidência forte observada divergente do hint preserva a divergência e é referência, sem autenticação adicional vedada por D03. Duas evidências fortes conflitantes impedem seleção automática de vendor. ONVIF genérico somente quando seguro e elegível; OEM/rebranding requer alias documentado e testado.
- **RATIONALE:** torna seleção determinística e auditável sem confiança probabilística inventada.
- **INVARIANTS:** sem substring arbitrária, sem first-response-wins e sem ocultar conflito.
- **CONTRACT_REQUIREMENTS:** contemplar todos os casos do §5; conflito forte exige política explícita de roteamento genérico seguro.
- **TEST_CRITERIA:** suite de casos de hint, divergências, sinais fortes/fracos, ausência, ordem invertida e rebranding; evidência observada forte divergente do hint preserva ambos, e duas evidências fortes conflitantes impedem seleção automática de vendor.
- **APPROVAL_STATUS:** `APPROVED_WITH_ADJUSTMENTS` (usuário, 2026-10-09).

### D07 — Retomada abrupta de lote

- **PROBLEM:** decidir checkpoint/resume para interrupção abrupta de lote.
- **EVIDENCE:** P2-A01 mantém `SINGLE`; lote e retomada não são requisito material desta expansão.
- **ALTERNATIVES:** incluir checkpoint agora; diferir para P4/P5 se houver requisito explícito futuro.
- **RECOMMENDATION:** diferir; retomar somente mediante exigência do usuário e decisão própria.
- **RATIONALE:** não introduzir persistência e complexidade fora do escopo.
- **INVARIANTS:** P2 não implementa `MULTI` nem concorrência.
- **CONTRACT_REQUIREMENTS:** decisão futura separada se necessária.
- **TEST_CRITERIA:** não aplicável a P2-A01.
- **APPROVAL_STATUS:** `DEFERRED`; MULTI e retomada de lote não são antecipados nesta fase.

## 9. Casos contratuais A–G

| Caso | Resultado exigido |
|---|---|
| A. ISAPI obtém identidade; ONVIF falha | Preservar valores e registrar tentativa falha. Status depende da cobertura; interromper auth após rejeição final. |
| B. ISAPI parcial; ONVIF complementa | Merge por campo e proveniência. `SUCCESS` depende somente dos três campos essenciais de `IDENTITY_V1`; timeout recuperado permanece no histórico. |
| C. Firmware diverge | Firmware é complementar: preservar candidatos e conflito sem last-write-wins, mas não bloquear `SUCCESS` se os três campos essenciais forem válidos e não houver conflito material neles; não consultar outra fonte apenas por firmware. |
| D. PREAUTH identifica fabricante; auth posterior expira | Fabricante sobrevive; descoberta parcial, sem alegar inventário autenticado; interromper auth conforme política. |
| E. Hint diverge de identidade forte observada | Manter declarado/observado/resolvido separados; preservar divergência e usar evidência forte observada como referência sem autenticação adicional vedada por D03. Se duas evidências fortes conflitarem, não escolher vendor automaticamente. |
| F. Fonte primária falha; secundária recupera | Permitir somente se faltar fabricante confirmado, modelo ou serial, sem rejeição final nem autorização negada, e dentro do budget; conta no limite de duas autenticações lógicas; recalcular status pelo relatório agregado. |
| G. HTTP 200 com payload inválido | `INVALID_RESPONSE`, nunca sucesso; preservar evidência anterior; fallback autenticado apenas se ainda faltar campo essencial de identidade e D03 permitir. |

## 10. Adapter ISAPI mínimo aprovado

O PoC aprovada limita-se a `GET /ISAPI/System/deviceInfo`, HTTP Digest, transporte isolado e parser XML seguro e limitado. Prioriza fabricante, modelo e serial; firmware e MAC são complementares. `deviceName` não é hostname; `hardwareVersion` não é HardwareId. HTTP 200 sem conteúdo válido não é sucesso. Integrar com adapter funcional, registry, diagnósticos, evidências e fluxo `SINGLE`; usar fixtures primeiro. Câmera real requer autorização operacional separada. Não equivale a P7 completo nem concede implementação.

## 11. Critérios de aceite T01–T15

Esta matriz define validação futura; não se deve executar testes nesta atividade.

| ID | Critério | Nível |
|---|---|---|
| T01 | Evidência válida sobrevive a falha posterior, exception e cancelamento. | UNIT |
| T02 | Exception e `FAILED` produzem status/dados agregados coerentes. | UNIT |
| T03 | Cliente/transporte Digest real faz challenge→Authorization→SOAP de sucesso; não envia WSSE junto e contabiliza a sequência. | TRANSPORT_FIXTURE |
| T04 | Fixture WSSE valida nonce/Created novos e ausência de HTTP Authorization. | TRANSPORT_FIXTURE |
| T05 | qop/algoritmo/challenge ausente, malformado ou incompatível dá mecanismo não suportado; sem fallback auth cego. | TRANSPORT_FIXTURE |
| T06 | 401 challenge→200 é sucesso; 401 final, 403 e SOAP NotAuthorized preservam categorias distintas e incertezas. | TRANSPORT_FIXTURE |
| T07 | Parser ISAPI cobre namespaces/versões, campos essenciais e complementares ausentes e mapeamentos semânticos corretos. | UNIT |
| T08 | HTTP 200 sem conteúdo válido, com erro vendor, 404/405, XML vazio/malformado nunca é sucesso; erro é classificado. | UNIT |
| T09 | Placeholder não é selecionável; duplicidade de registro é rejeitada ou substituída apenas por regra explícita. | UNIT |
| T10 | Allowlist bloqueia Set/reboot/configuração/usuários; SOAP POST só executa operação READ_ONLY aprovada. | UNIT |
| T11 | `/galaxis` não resolve Axis; hint, sinal fraco/forte, conflitos, OEM e ordem invertida seguem contrato. | UNIT |
| T12 | Canários de segredo não aparecem em repr/log/UI/Excel/attempts; trust_env/netrc não fornece auth; cross-origin/XAddr divergente e TLS inválido sem downgrade são bloqueados. | INTEGRATION + TRANSPORT_FIXTURE |
| T13 | Uma família nativa por target; unknown usa ONVIF elegível; cobertura de `IDENTITY_V1` satisfeita não consulta segunda fonte; auth reject final ou autorização negada interrompe; fallback autenticado só cobre falta de fabricante/modelo/serial e respeita credencial/limites. | UNIT + INTEGRATION |
| T14 | Casos A–G confirmam merge independente da ordem, nenhum overwrite por vazio, conflito/proveniência e status recalculado; firmware ausente/divergente não bloqueia `SUCCESS` quando os essenciais são válidos e sem conflito material. | UNIT |
| T15 | Requests reais contam handshake interno; no máximo um retry elegível; sem operação após deadline/cancelamento; discovery não duplica capability. | UNIT + INTEGRATION |

Regressão P1 deve ser considerada na futura implementação; baseline histórica informada: 51 testes aprovados. Não executar nem inferir resultado atual nesta atividade.

## 12. Compatibilidade futura com MULTI

Somente registrar requisitos de compatibilidade futura; P2 não implementa lote ou concorrência. Futuro XLSX deve preservar `row_id`, linhas com IP duplicado como linhas distintas, credenciais/sessões/resultados por linha, ordem, resultado individual, cancelamento, exportação sem senha e parciais. Se aprovado no futuro, `ThreadPoolExecutor` teria default 8 e faixa 1–32; autenticação por IP seria serializada e credenciais/resultados nunca compartilhados entre linhas. Retomada abrupta fica diferida em D07.

## 13. Sequência incremental recomendada

1. **Incremento 1:** resolver F01–F03; tipos mínimos de coleta/diagnóstico; integração `SINGLE` e regressão.
2. **Incremento 2:** ISAPI Hikvision mínimo, registry funcional, integração `SINGLE` e testes.
3. **Incremento 3:** prova operacional separadamente autorizada e comparação controlada com ONVIF Digest.
4. **Incremento 4:** inventário de rede, protocolos, proveniência/completude e regressão.

Esta sequência é recomendação de planejamento, não autorização de implementação. Roadmap P3–P12 permanece como definido nas fontes canônicas.

## 14. Pendências de aprovação e encerramento

D00 permanece `APPROVED`; D01 foi `APPROVED_WITH_REVISION` e D02–D06 foram `APPROVED_WITH_ADJUSTMENTS` pelo usuário em 2026-10-09. D07 permanece `DEFERRED`; não se antecipa MULTI nem retomada de lote. O contrato P2 está `APPROVED`, com P0 e P1 `CLOSED`; a fase P2 não está encerrada e `P2_IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`. A aprovação não autoriza implementação, consultas a câmeras reais nem reabre P1. O contrato histórico P1 e seus 14 campos permanecem compatíveis.

### Referências de autoridade

Consultar `AGENTS.md`, `docs/audit/ARCH_AUDIT_01_REPORT.md`, `docs/continuity/planning/ROADMAP.md`, `docs/continuity/planning/EXECUTION_PLAN.md`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/CONTINUITY_RECORD.md`, `docs/continuity/ACTIVE_AUTHORITY_MAP.md`, `docs/continuity/START_HERE.md`, `docs/continuity/handoff/LAST_HANDOFF.md`, `docs/contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md` e as políticas PM-01/02/03/04/05 e protocolo de continuidade 3.0 indicados no entrypoint do projeto. Em caso de divergência, prevalecem as fontes canônicas e a decisão do usuário.
