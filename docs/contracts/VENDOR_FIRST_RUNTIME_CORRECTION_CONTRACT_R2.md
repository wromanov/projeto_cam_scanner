# Contrato R2 — Correção do fluxo runtime Vendor-First

```text
PROJECT = projeto_cam_scanner
ACTIVITY = VENDOR_FIRST_RUNTIME_CORRECTION_R2
EXECUTION_MODE = MULTIAGENT
DOCUMENT_STATUS = APPROVED_CONTRACTUAL_SCOPE
APPROVAL_STATUS = USER_APPROVED_REFINEMENT
IMPLEMENTATION_AUTHORIZATION = GRANTED_OFFLINE_R2_ONLY
IMPLEMENT_TEST_VALIDATE_AUTHORIZATION = GRANTED_R2_OFFLINE_ONLY
REAL_CAMERA_AUTHORIZATION = NOT_GRANTED
BUILD_AUTHORIZATION = NOT_GRANTED
PUBLISH_OR_GIT_CONSEQUENTIAL_AUTHORIZATION = NOT_GRANTED
AUTHORIZED_WORK_MODE = IMPLEMENT_TEST_VALIDATE
HOMOLOGATION_STATUS = DEFERRED_TO_AC_19
SCOPE = ordem de descoberta/coleta e preservação de diagnóstico SINGLE/MULTI
BASELINE = VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT.md (R1)
ACCEPTANCE = AC_01_TO_AC_18_AND_AC_20
REAL_HOMOLOGATION = AC_19_RESERVED_AND_DEFERRED
```

Este documento consolida a R1 e o refinamento contratual aprovado pelo usuário para entrada opcional de hint SINGLE, exportação de diagnósticos MULTI e critérios verificáveis. Preserva os contratos P1/P2/PRE-P12 e não os altera. O usuário autorizou implementação offline e execução de testes/regressão estritamente para o delta R2. Essa autorização não inclui AC-19/homologação real, acesso a câmera, nova build, publicação ou ações Git consequenciais. AC-19 fica reservado e fora desta implementação.

## 1. Objetivo

Fazer com que a coleta use primeiro um adapter proprietário quando um hint de fabricante elegível já permitir esse roteamento, e que use discovery ONVIF anônimo, curto e limitado quando o fabricante continuar desconhecido. Definir um hint de fabricante opcional em SINGLE: em branco, permanecem as três entradas obrigatórias históricas; preenchido, aplica exatamente as regras de declaração e elegibilidade usadas pelo hint MULTI. Para MULTI, tornar visíveis as tentativas sanitizadas em uma aba `DIAGNOSTICOS` do XLSX, associadas à linha e ordenadas por linha/tentativa. Evitar uma chamada obrigatória de `ONVIF.GetCapabilities` antes do adapter em casos em que a direção P2 aprovada dispensa esse preauth. Preservar falhas TLS como encerramento fail-closed de novas operações de rede, sem downgrade ou fallback posterior ao erro TLS.

Manter evidências e tentativas sanitizadas visíveis nos diagnósticos SINGLE e MULTI, sem adicionar campos ao contrato histórico de 14 campos de `CameraResult` nem persistir conteúdo bruto de requests/responses. O hint SINGLE opcional e a aba MULTI `DIAGNOSTICOS` fazem parte do escopo contratual R2 aprovado.

## 2. Base documental e factual

### 2.1 Direção normativa já aprovada

- P1 define `VENDOR_FIRST_WHEN_KNOWN`, hint de fabricante como `STRONG_HINT`, adapter nativo quando conhecido e ONVIF como complemento/fallback; para fabricante ausente, exige identificação pré-autenticação/read-only. P1 também define `MANUFACTURER_MISMATCH = DETECT_AND_REPORT` e proíbe tentativa de credenciais em fabricantes diferentes. Fonte: `docs/contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`, §§2–2.2.
- P2 está marcado `APPROVED` e determina `HYBRID_CAPABILITY_DRIVEN_WITH_VENDOR_PREFERENCE`. Hint confiável com adapter funcional capaz de cobrir os campos não exige preauth ONVIF. Fabricante desconhecido usa discovery anônimo limitado; adapter proprietário só é preferido quando evidência/capability justificam. Hint não confirma fabricante; sinais fortes conflitantes impedem seleção vendor automática. Fonte: `docs/contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`, metadados, §§3–5 e D00–D06.
- P2 limita auth a no máximo duas tentativas lógicas por câmera e só permite a tentativa secundária quando ainda faltar fabricante confirmado, modelo ou serial, sem rejeição final/negação de autorização e dentro do budget. Fonte: `docs/contracts/P2_COLLECTION_STRATEGY_EXPANSION.md`, §4.
- PRE-P12 exige TLS verificado; certificado inválido resulta em `TLS_ERROR`, sem `verify=False`, TOFU ou fallback/downgrade para HTTP. Deadline, budgets, cancelamento, tentativas e evidências pertencem ao contexto/relatório da coleta; não repetir discovery equivalente nem `GetCapabilities`. Fonte: `docs/contracts/PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md`, §§5–8.
- PRE-P12 preserva `CameraResult` com 14 campos e define `CollectionReport` como fonte agregada de evidências e tentativas, com diagnóstico sanitizado por operação. Fonte: `docs/contracts/PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md`, §§5, 7 e 13.

### 2.2 Comportamento observado no checkout

O fluxo atual chama o discoverer antes de ler `context.manufacturer_hint` ou consultar o registry: `src/cam_scanner/cameras/strategy.py:47-95`. A implementação de discovery anônimo inclui `GetCapabilities`: `src/cam_scanner/cameras/preauth.py:114-116`. Após essa etapa, a estratégia resolve o fabricante e seleciona o adapter do registry: `src/cam_scanner/cameras/strategy.py:87-123`.

Se a etapa prévia resulta em `TLS_ERROR`, a estratégia marca a falha TLS e retorna antes da seleção/coleta do adapter: `src/cam_scanner/cameras/strategy.py:62-85`. O contexto mantém o marcador de falha TLS e impede novas operações de rede após essa falha: `src/cam_scanner/application/collection_context.py:346-348` e `:354-358`.

MULTI passa o hint da linha ao contexto: `src/cam_scanner/application/multi_workflow.py:176-184` e `:227-240`; o fluxo SINGLE atualmente não fornece hint no caminho de criação do contexto. Este R2 registra a decisão aprovada para SINGLE acrescentar um campo opcional de fabricante: vazio mantém IP, username e password como as três entradas obrigatórias históricas; preenchido, o valor é `DECLARED`, direciona roteamento sob as regras idênticas ao hint MULTI e não comprova identidade. Isso não reabre nem altera retroativamente P1.

O relatório agregado contém tentativas, mas a projeção final de MULTI é um `CameraResult` e o artefato XLSX não representa a sequência completa por operação. P1 mantém diagnósticos de SINGLE; P2 e PRE-P12 requerem preservar relatório e provenance. R2 define a aba `DIAGNOSTICOS` no XLSX de saída, associando cada tentativa a `LINHA` e ordenando por linha e tentativa, sem substituir nem alterar a aba/inventário existente, sem segredos e sem adicionar campos a `CameraResult`.

O registry contém `Bosch`, mas o `BoschAdapter` atual registra `ENDPOINT_UNSUPPORTED`/`SKIPPED` e informa que não fornece fabricante, modelo e serial por coleta nativa documentada (`src/cam_scanner/cameras/registry.py:33-46`; `src/cam_scanner/cameras/manufacturers/bosch.py:1-5,20-34`). Portanto, presença no registry não demonstra elegibilidade nem cobertura dos campos essenciais.

O snapshot `docs/continuity/PROJECT_STATE.md` registra `OPERATIONAL_HOMOLOGATION_PENDING`. A falha relatada pelo usuário não veio acompanhada, neste checkout, de log runtime verificável; a causa descrita nesta seção é derivada do código e dos contratos, não de confirmação independente da execução real da homologação.

## 3. Comportamento esperado proposto

### 3.1 Entradas e distinções de fabricante

Manter separadas as dimensões:

- `DECLARED`: hint fornecido por fonte de entrada contratada, preservado como declaração e normalizado para lookup;
- `OBSERVED`: sinal obtido por operação realmente executada, com fonte/protocolo/operação e confiança;
- `RESOLVED`: fabricante selecionável após aplicar as regras aprovadas de confiança, conflito e capability.

Hint direciona roteamento, mas não prova fabricante. Sinal fraco não substitui hint nem vira evidência forte. Evidência estruturada forte incompatível com o hint deve ser preservada e reportada como divergência; sinais fortes incompatíveis entre si impedem seleção automática de adapter proprietário. Não selecionar por substring, primeiro resultado, ordem de rede ou tentativa de login.

Um hint só permite pular preauth obrigatório se normalizar para uma família reconhecida, houver adapter cuja cobertura dos campos requeridos esteja demonstrada por suporte documentado e testado nas interfaces/evidências existentes, e não houver conflito forte já conhecido. Registro no registry, isoladamente, não basta: por exemplo, o BoschAdapter consta no registry, mas não fornece manufacturer/model/serial pela fonte nativa; esse caso não pode dispensar a identificação/fallback autorizado. Placeholder ou suporte não demonstrado não satisfaz o critério. Essa verificação usa suporte existente documentado/testado e não exige registry, schema, interface ou framework novo. Caso essas condições não sejam demonstráveis, seguir o caminho de fabricante desconhecido. Um hint jamais confirma identidade por si só.

### 3.2 Fluxo determinístico

1. Criar um único `CollectionContext` antes de qualquer operação e associar a ele target/linha, hint existente (MULTI ou SINGLE opcional quando aprovado), deadline, budgets, cancelamento, ledger de autenticação, sessões e relatório agregado. O contexto não pode ser recriado para reabrir rede nem reiniciar budget.
2. Validar target, política de destino/TLS, campos requeridos, hint declarado e elegibilidade do adapter por seu suporte existente documentado/testado, sem fazer I/O.
3. Se houver hint reconhecido, adapter com suporte documentado/testado para cobrir os campos requeridos e nenhum conflito forte conhecido, invocar o adapter proprietário como fonte primária READ_ONLY. Não invocar `GetCapabilities` apenas como precondição para esse roteamento.
4. Após coleta proprietária, validar e registrar evidências, proveniência e tentativas. Confrontar a observação do adapter com o hint segundo as regras de conflito da P2. A divergência não pode ser substituída silenciosamente pelo valor declarado.
5. Se houver fabricante desconhecido ou hint inelegível, executar discovery anônimo curto e limitado, conforme orçamento P2/PRE-P12. Reutilizar o resultado dessa discovery na resolução/seleção; não repetir `GetCapabilities` nem descoberta equivalente. Se houver fabricante fortemente resolvido e adapter com suporte documentado/testado para os campos requeridos, selecioná-lo conforme a política aprovada; se continuar desconhecido ou sem adapter utilizável, ONVIF genérico é elegível quando seguro e permitido.
6. ONVIF autenticado pode complementar campos essenciais ainda ausentes ou servir de fallback permitido. Só iniciar tentativa secundária se ainda faltar fabricante confirmado, modelo ou serial, D03 permitir, não houver rejeição final/negação de autorização, cancelamento/deadline não tiver ocorrido e budgets restantes forem suficientes.
7. Se a coleta do adapter falhar sem erro TLS, rejeição final ou negação de autorização, ONVIF genérico pode ser considerado como fallback permitido, conforme destino, elegibilidade e budgets. O relatório deve conservar a falha proprietária e evidência já validada. Falha de autenticação final e autorização negada fecham operações autenticadas posteriores conforme D03.
8. Ao ocorrer `TLS_ERROR` em qualquer fonte, marcar o contexto como falha TLS e encerrar novas operações de rede para aquele target/coleta. Não trocar HTTPS por HTTP, não usar `verify=False`, não tentar outro adapter, discovery ou fallback de rede após o erro. Preservar as tentativas/evidências anteriores e o diagnóstico da falha.
9. Encerrar com status derivado do relatório/proveniência/cobertura e preservar `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED` ou `CANCELLED` conforme os contratos. No MULTI, exportar uma linha por `CollectionAttempt` sanitizada à aba `DIAGNOSTICOS`, com referência `LINHA` e ordem determinística por linha/tentativa. Não afirmar inventário completo por haver apenas hint ou discovery parcial.

Esse fluxo não define endpoints de fabricante, modelos de payload adicionais, nova ordem entre famílias, política de confiança de certificado ou novos campos públicos. O inventário de adapters/famílias e seus endpoints só pode seguir fontes já autorizadas e contratos próprios.

## 4. Ordem atual e ordem esperada

| Cenário | Ordem atual observada | Ordem proposta conforme P2 |
|---|---|---|
| MULTI com hint e adapter elegível | preauth ONVIF anônimo (`GetCapabilities`) → resolver → adapter proprietário → ONVIF complementar/fallback | validar hint e suporte existente documentado/testado sem I/O → adapter proprietário → complementar/fallback apenas se elegível |
| SINGLE com campo opcional em branco | preauth ONVIF anônimo → resolver → adapter, se resolvido → ONVIF complementar/fallback | mesmas três entradas obrigatórias P1; discovery anônimo limitada → resolver → adapter quando evidência e suporte existente documentado/testado justificarem; senão ONVIF genérico |
| SINGLE com hint opcional preenchido (R2) | não existe essa entrada hoje | tratar como `DECLARED` e aplicar as mesmas regras de hint MULTI; elegibilidade pode dispensar preauth obrigatório |
| Qualquer cenário após `TLS_ERROR` | contexto bloqueia novas operações de rede; no preauth inicial o adapter não chega a ser considerado | mesma parada fail-closed; a condição deve ser evitada quando preauth não for obrigatório, mas não contornada depois de TLS error |

## 5. Causa raiz e conformidade

**Causa raiz confirmada no código:** o fluxo implementa discovery prévia como etapa incondicional anterior ao hint/registry, embora P2 dispense preauth ONVIF obrigatório quando há hint confiável e adapter funcional. Isso força `GetCapabilities` em cenários que deveriam poder iniciar pelo adapter. Se essa operação produz `TLS_ERROR`, a parada de rede obrigatória e contratual ocorre antes que a estratégia considere o adapter.

**Não é causa raiz:** o bloqueio pós-`TLS_ERROR` no `CollectionContext`. Essa parada é exigida por PRE-P12 e deve continuar fail-closed.

**Diagnóstico MULTI:** o relatório e o contexto transitório existem durante a coleta, mas as tentativas por operação não permanecem visíveis na projeção `CameraResult`/XLSX. A proposta exige tornar a sequência sanitizada acessível no diagnóstico do lote, mantendo o resultado público P1 compatível.

**Conformidade atual:** divergente de P2 na ordem condicional do preauth, no caso hint elegível; conforme à exigência de fail-closed após `TLS_ERROR`; parcialmente divergente quanto à visibilidade/preservação do relatório MULTI para o operador. Não há evidência local suficiente para declarar o resultado de homologação real ou quantificar em quais câmeras a divergência ocorreu.

## 6. Correção mínima proposta

- Reordenar apenas a decisão inicial da estratégia para avaliar hint, registry e suporte existente documentado/testado antes de exigir discovery ONVIF.
- Preservar discovery limitada para fabricante desconhecido e ONVIF genérico/fallback quando autorizado.
- Manter `CollectionContext` como autoridade de destino, TLS, auth, deadline, budget e cancelamento; `TLS_ERROR` sempre encerra novas operações de rede.
- Exportar no XLSX MULTI uma aba `DIAGNOSTICOS`, uma linha por tentativa sanitizada de `CollectionAttempt`, associada por `LINHA` e ordenada por linha/tentativa. Colunas: `LINHA`, `ETAPA`, `PROTOCOLO`, `OPERACAO`, `OUTCOME`, `CATEGORIA`, `DURACAO`, `CODIGO` e `STATUS`; incluir código/status somente se estiverem disponíveis e seguros. Validar os valores como células de dados, neutralizando fórmulas de planilha. Não incluir body, header, URL, exceção bruta, credencial ou valor de evidência; preservar a aba e o inventário existentes.
- Não alterar endpoints, contratos canônicos existentes, assinatura pública de `CameraResult`, segurança TLS ou a lista/ordem de fabricantes. O hint opcional SINGLE e a nova aba `DIAGNOSTICOS` são decisões R2 aprovadas para implementação offline dentro desta autorização.

## 7. Critérios de aceite propostos

| ID | Fixture/verificação | Resultado requerido |
|---|---|---|
| AC-01 | MULTI com hint reconhecido, adapter registrado e suporte documentado/testado; discovery ONVIF com spy que falha se chamado | O adapter vendor coleta campos suportados; `GetCapabilities` não é chamado; relatório registra tentativas e proveniência vendor. |
| AC-02 | MULTI sem hint, fixture anônima com sinal estruturado autorizado de fabricante conhecido | A descoberta usa somente operações READ_ONLY aprovadas; `GetCapabilities` ocorre no máximo uma vez; a resolução e seleção do adapter decorrem do sinal estruturado, não de substring/ordem. |
| AC-03 | MULTI sem hint, fixture sem fabricante resolvível; repetir elegibilidade com Bosch registrado mas sem cobertura nativa de manufacturer/model/serial | O caminho mantém identificação automática limitada e usa ONVIF genérico quando permitido; registry membership isolada não dispensa discovery; não inventa endpoint, fabricante ou adapter. |
| AC-04 | Adapter vendor retorna falha não TLS e não há rejeição final/negação; ONVIF genérico está autorizado e há budget | Fallback ONVIF é chamado somente uma vez e dentro do escopo; relatório conserva tentativa vendor falha, tentativa ONVIF e evidência anterior. |
| AC-05 | Discovery anônima retorna `TLS_ERROR` por certificado inválido | Contexto fecha rede para o target; nenhum adapter, retry TLS, ONVIF fallback ou downgrade HTTP é chamado; tentativa TLS fica registrada. |
| AC-06 | Adapter vendor retorna `TLS_ERROR` por certificado inválido | Nenhuma operação de rede posterior ocorre; ONVIF não é chamado; verificação TLS permanece habilitada. |
| AC-07 | Hint declarado diverge de um sinal estruturado forte na fixture | `DECLARED`, `OBSERVED` e `RESOLVED` ficam distinguíveis; divergência é preservada/reportada e resolução segue P2 sem substituir silenciosamente a evidência forte. |
| AC-08 | Fixture com dois sinais fortes incompatíveis, em ordens de resposta invertidas | Seleção vendor automática é bloqueada em ambas as ordens; conflito é explícito; ONVIF genérico só ocorre se seguro e permitido pelo plano. |
| AC-09 | Fixture contém apenas sinal fraco, como `Server`, realm, substring, OUI ou `deviceName` | Sinal não é promovido a fabricante confirmado, não sobrepõe hint e não seleciona vendor por ordem/substring; segue a descoberta/fallback autorizado. |
| AC-10 | SINGLE com hint opcional vazio | UI mantém IP, username e password como três campos obrigatórios; fluxo automático identifica sem pedir fabricante e mantém uma única discovery limitada. |
| AC-11 | SINGLE com hint reconhecido preenchido e adapter elegível | Hint é registrado como `DECLARED`; adapter é selecionado sob as mesmas regras do MULTI e `GetCapabilities` não é precondição obrigatória. Hint isolado não resulta em fabricante confirmado. |
| AC-12 | SINGLE com hint preenchido desconhecido, sem adapter ou sem suporte demonstrado | Hint permanece declarado; fluxo prossegue pela identificação automática autorizada e ONVIF genérico permitido, sem travar nem tentar credenciais em outros fabricantes. |
| AC-13 | MULTI com fixture de várias linhas e várias tentativas por linha | Aba `DIAGNOSTICOS` contém uma linha por `CollectionAttempt`, associada por `LINHA`; ordenação é por linha de entrada e ordem de tentativa; colunas correspondem ao esquema da seção 6. |
| AC-14 | Tentativas contêm valores-canário de username/password, tokens, URL com userinfo, body, header, exception e protocolo/code/status | Nenhum segredo, conteúdo bruto, URL ou exception aparece na aba; somente campos sanitizados permitidos são exportados; códigos/status só aparecem quando seguros. |
| AC-15 | Campos de tentativa controlados por fixture começam com `=`, `+`, `-`, `@`, tab, CR ou caracteres Unicode de controle | XLSX abre esses valores como dados inertes; nenhuma célula executa fórmula ou comando; linhas de dados legítimas continuam associadas à `LINHA` correta. |
| AC-16 | Contexto de autenticação fixture: challenge Digest, sucesso, rejeição final e 403 | Challenge Digest conta como uma tentativa lógica, mas cada troca física consome budget; limite D03 é no máximo duas tentativas lógicas; após rejeição final/403 não há qualquer auth posterior nem troca/fallback de família. |
| AC-17 | Contexto compartilhado com relógio/budget fake entre discovery, vendor e ONVIF; casos com deadline/cancelamento | Deadline monotônico e budgets não reiniciam; nenhuma request inicia após esgotamento/cancelamento; limites P2/PRE-P12 e isolamento por linha são preservados. |
| AC-18 | Construção e exportação dos resultados fixture de sucesso, parcial, falha e conflito | `CameraResult` mantém exatamente os 14 campos P1; tentativas/proveniência permanecem em `CollectionReport`/`DIAGNOSTICOS`, sem extension bag ou segredo; status não infere identidade do hint isolado. |
| AC-19 | Homologação READ_ONLY contra câmera/modelo real autorizado | **RESERVADO E DEFERIDO.** Não pertence à implementação coberta por este contrato; requer autorização, target/credenciais e procedimento operacional próprios. Nenhum resultado offline satisfaz este aceite. |
| AC-20 | Relatório de validação do delta R2 autorizado | Entrega matriz AC-01–AC-18 e AC-20 com estado/evidência por critério; logs dos testes focados; regressão integral posterior ao delta com pass/fail/skipped/deselected, versão Python e comando; Ruff/lint dos arquivos alterados e `git diff --check`. Avalia somente os critérios PRE-P12 impactados pelo delta: A, B, D, H, I, K, L, M, Q, R e T. Registra Gate 2 (regressão integrada aplicável), Gate 3 (revisão independente do delta), Gate 4 (reavaliação de prontidão limitada ao R2) e Gate V (suíte integral pós-delta). O snapshot P12 de `docs/continuity/PROJECT_STATE.md` em 2026-10-19 registra Gate 2/3/4/V como PASS da etapa antecedente; esses resultados são contexto/evidência anterior, nunca prova dos critérios R2. Não reabre automaticamente toda a matriz PRE-P12 A–V. Gate 5/build/publicação, câmera real e AC-19 estão fora da autorização. Nenhum gate é declarado PASS sem evidência própria. |

AC-01–AC-18 e AC-20 usam fakes, spies e fixtures determinísticas, confirmando requests feitos/omitidos, relatórios e bytes/células exportados. AC-19 permanece separado. A autorização R2 permite implementação e validação offline descritas, mas este documento não afirma que qualquer critério ou gate já passou.

## 8. Fora de escopo e guardrails

- Alterar os contratos canônicos P1/P2/PRE-P12 ou `PROJECT_STATE` nesta atividade.
- Desabilitar validação TLS, usar `verify=False`, TOFU, degradação HTTPS→HTTP ou fallback de rede após `TLS_ERROR`.
- Autenticar todos os fabricantes, testar credenciais em adapters distintos, trocar família após rejeição, ou exceder D03.
- Criar endpoint proprietário especulativo, alterar roadmap/adapters suportados, inserir autenticação secundária para firmware/dados complementares, ou redefinir campos/status de `CameraResult`.
- Acessar câmera real/AC-19, executar nova build, publicar, ou realizar commit/push e outras ações Git consequenciais.
- Alegar suporte universal, implementação concluída, homologação real validada ou aprovação da presente proposta sem evidência/decisão correspondente.

## 9. Decisões e pontos condicionais

- A direção híbrida e suas invariantes de P2/PRE-P12 são tratadas como aprovadas pelas fontes citadas; esta proposta não as reaprova nem expande.
- **DECISÃO R2 — hint SINGLE:** entrada opcional de fabricante aprovada. Vazia, preserva os três campos obrigatórios históricos IP/username/password; preenchida, segue exatamente as regras de hint MULTI (`DECLARED`, orientação de roteamento, nunca prova). Não reabre P1.
- **DECISÃO R2 — diagnóstico MULTI:** aba `DIAGNOSTICOS` aprovada, com as colunas/ordenação da seção 6, preservando aba/inventário existente e os 14 campos de `CameraResult`.
- **AUTORIZAÇÃO DE EXECUÇÃO:** limitada à implementação offline e testes/regressão de AC-01–AC-18 e AC-20. Não inclui AC-19/câmera real, build, publicação, nem Git consequencial.
- AC-19 permanece reservado para homologação real futura; não é aceite nem autorização desta implementação. A ocorrência relatada continua sem log verificável no checkout.

```text
ROOT_CAUSE_FROM_CODE = PREAUTH_ONVIF_UNCONDITIONAL_BEFORE_HINT_AND_REGISTRY
TLS_FAIL_CLOSED = REQUIRED_AND_RETAINED
MULTI_DIAGNOSTICS_SHEET = APPROVED_IN_R2
SINGLE_OPTIONAL_HINT = APPROVED_IN_R2
AC_19_REAL_HOMOLOGATION = RESERVED_DEFERRED
CANONICAL_CONTRACT_CHANGES = NONE
IMPLEMENTATION_STATUS = NOT_ASSESSED
OPERATIONAL_HOMOLOGATION = NOT_ASSESSED_BY_THIS_DOCUMENT
CAMERA_ACCESS = NOT_AUTHORIZED
BUILD_OR_PUBLISH = NOT_AUTHORIZED
```
