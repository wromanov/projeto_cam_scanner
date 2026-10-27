# Proposta de contrato — Correção do fluxo runtime Vendor-First

```text
PROJECT = projeto_cam_scanner
ACTIVITY = VENDOR_FIRST_RUNTIME_CORRECTION_CONTRACT
DOCUMENT_STATUS = PROPOSED
APPROVAL_STATUS = NOT_RECORDED
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED_BY_THIS_DOCUMENT
HOMOLOGATION_STATUS = NOT_ESTABLISHED_BY_THIS_DOCUMENT
SCOPE = ordem de descoberta/coleta e preservação de diagnóstico SINGLE/MULTI
PROPOSED_DECISIONS_PENDING_APPROVAL = SINGLE_OPTIONAL_MANUFACTURER_HINT; MULTI_DIAGNOSTICS_XLSX_SHEET
```

Este documento propõe a correção mínima do fluxo runtime descrito abaixo. Ele registra uma proposta derivada da direção já aprovada em P2 e dos limites vigentes de segurança. Não aprova arquitetura nova, não altera os contratos P1/P2/PRE-P12 e não atesta implementação ou homologação. Qualquer implementação depende de autorização própria.

## 1. Objetivo

Fazer com que a coleta use primeiro um adapter proprietário quando um hint de fabricante elegível já permitir esse roteamento, e que use discovery ONVIF anônimo, curto e limitado quando o fabricante continuar desconhecido. Propor um hint de fabricante opcional em SINGLE: em branco, permanecem as três entradas obrigatórias históricas; preenchido, aplica exatamente as regras de declaração e elegibilidade usadas pelo hint MULTI. Para MULTI, tornar visíveis as tentativas sanitizadas em uma aba `DIAGNOSTICOS` do XLSX, associadas à linha e ordenadas por linha/tentativa. Evitar uma chamada obrigatória de `ONVIF.GetCapabilities` antes do adapter em casos em que a direção P2 aprovada dispensa esse preauth. Preservar falhas TLS como encerramento fail-closed de novas operações de rede, sem downgrade ou fallback posterior ao erro TLS.

Manter evidências e tentativas sanitizadas visíveis nos diagnósticos SINGLE e MULTI, sem adicionar campos ao contrato histórico de 14 campos de `CameraResult` nem persistir conteúdo bruto de requests/responses. As decisões de hint opcional SINGLE e aba MULTI `DIAGNOSTICOS` são propostas deste documento e aguardam aprovação.

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

MULTI passa o hint da linha ao contexto: `src/cam_scanner/application/multi_workflow.py:176-184` e `:227-240`; o fluxo SINGLE atualmente não fornece hint no caminho de criação do contexto. Este contrato propõe que SINGLE acrescente um campo opcional de fabricante: vazio mantém IP, username e password como as três entradas obrigatórias históricas; preenchido, o valor é `DECLARED`, direciona roteamento sob as regras idênticas ao hint MULTI e não comprova identidade. A proposta está pendente de aprovação e não reabre nem altera retroativamente P1.

O relatório agregado contém tentativas, mas a projeção final de MULTI é um `CameraResult` e o artefato XLSX não representa a sequência completa por operação. P1 mantém diagnósticos de SINGLE; P2 e PRE-P12 requerem preservar relatório e provenance. A proposta é adicionar ao XLSX de saída a aba `DIAGNOSTICOS`, associando cada tentativa a `LINHA` e ordenando por linha e tentativa, sem substituir nem alterar a aba/inventário existente, sem segredos e sem adicionar campos a `CameraResult`.

O snapshot `docs/continuity/PROJECT_STATE.md` registra `OPERATIONAL_HOMOLOGATION_PENDING`. A falha relatada pelo usuário não veio acompanhada, neste checkout, de log runtime verificável; a causa descrita nesta seção é derivada do código e dos contratos, não de confirmação independente da execução real da homologação.

## 3. Comportamento esperado proposto

### 3.1 Entradas e distinções de fabricante

Manter separadas as dimensões:

- `DECLARED`: hint fornecido por fonte de entrada contratada, preservado como declaração e normalizado para lookup;
- `OBSERVED`: sinal obtido por operação realmente executada, com fonte/protocolo/operação e confiança;
- `RESOLVED`: fabricante selecionável após aplicar as regras aprovadas de confiança, conflito e capability.

Hint direciona roteamento, mas não prova fabricante. Sinal fraco não substitui hint nem vira evidência forte. Evidência estruturada forte incompatível com o hint deve ser preservada e reportada como divergência; sinais fortes incompatíveis entre si impedem seleção automática de adapter proprietário. Não selecionar por substring, primeiro resultado, ordem de rede ou tentativa de login.

Um hint só permite pular preauth obrigatório se normalizar para uma família reconhecida, houver adapter registrado cuja capacidade de cobrir os campos requeridos esteja documentada e testada nas interfaces/evidências existentes, e não houver conflito forte já conhecido. Placeholder ou suporte não demonstrado não satisfaz o critério. Essa verificação usa o suporte existente documentado/testado e não exige registry, schema, interface ou framework novo. Caso essas condições não sejam demonstráveis, seguir o caminho de fabricante desconhecido. Um hint jamais confirma identidade por si só.

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
| SINGLE com hint opcional preenchido (proposta pendente) | não existe essa entrada hoje | tratar como `DECLARED` e aplicar as mesmas regras de hint MULTI; elegibilidade pode dispensar preauth obrigatório |
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
- Não alterar endpoints, contratos canônicos existentes, assinatura pública de `CameraResult`, segurança TLS ou a lista/ordem de fabricantes. O hint opcional SINGLE e a nova aba são decisões propostas neste contrato, ainda pendentes de aprovação.

## 7. Critérios de aceite propostos

| ID | Verificação necessária | Resultado esperado |
|---|---|---|
| AC-01 | MULTI com hint reconhecido e adapter com suporte documentado/testado para os campos requeridos; transporte ONVIF configurado para falhar TLS se consultado | adapter é invocado sem chamada `GetCapabilities`; dados e tentativa do adapter são registrados com proveniência |
| AC-02 | SINGLE sem hint | discovery anônima limitada é executada uma vez; `GetCapabilities` não é duplicado; resolução usa a evidência retornada |
| AC-03 | Hint normalizado sem adapter registrado ou sem suporte documentado/testado para os campos requeridos | hint não é tratado como prova; caminho unknown/discovery ou fallback genérico permitido segue deterministicamente |
| AC-04 | Hint conflita com evidência forte observada | fabricante declarado e observado permanecem distinguíveis; conflito é reportado; nenhum adapter é escolhido apenas pela ordem/hint contra a regra P2 |
| AC-05 | `TLS_ERROR` na discovery do cenário unknown | nenhuma operação de rede subsequente ocorre; sem adapter tardio, ONVIF fallback, HTTP downgrade ou retry TLS; tentativa TLS aparece sanitizada |
| AC-06 | `TLS_ERROR` no adapter após roteamento por hint | nenhuma operação de rede subsequente ocorre; não há ONVIF fallback; validação TLS permanece habilitada |
| AC-07 | Falha vendor que não seja TLS/auth final/negação; ONVIF fallback permitido, dentro de destino e budget | fallback acontece somente quando elegível; relatório conserva a falha vendor, fallback e evidência útil |
| AC-08 | Primeira autenticação termina em rejeição final ou autorização negada | zero autenticações/operações autenticadas subsequentes; hint, evidência e estado parcial são preservados |
| AC-09 | Campos essenciais já completos após fonte primária | não ocorre autenticação secundária nem chamada só para complementar dado não essencial |
| AC-10 | Budget, deadline ou cancelamento esgotado entre fontes | nenhuma nova chamada/request é emitido; deadline e budget não reiniciam |
| AC-11 | MULTI com mais de uma tentativa por linha, inclusive falha | aba `DIAGNOSTICOS` tem uma linha por tentativa sanitizada, associada por `LINHA` e ordenada por linha/tentativa, com etapa, protocolo, operação, outcome, categoria, duração e código/status quando seguros |
| AC-12 | Verificação estrutural e de exportação | `CameraResult` mantém exatamente 14 campos; aba/inventário XLSX existente é preservado; `DIAGNOSTICOS` não contém segredo, conteúdo bruto ou fórmulas executáveis |
| AC-13 | Regressão SINGLE/MULTI e adapters/ONVIF existentes | fluxos atuais continuam determinísticos, READ_ONLY, isolados por linha e limitados pelos budgets; nenhuma chamada a endpoint não contratado |
| AC-14 | SINGLE com hint opcional em branco e preenchido | IP, username e password continuam obrigatórios; o novo campo aceita vazio; quando preenchido, o hint é apenas declaração e aplica as regras MULTI, sem tratá-lo como prova |

Os testes devem usar doubles/fixtures determinísticos e confirmar chamadas efetivamente feitas ou omitidas, além do conteúdo do relatório. A aprovação dos critérios deve ser demonstrada na futura atividade autorizada; este contrato não declara nenhum critério PASS.

## 8. Fora de escopo e guardrails

- Alterar código, testes, contrato P1, P2 ou PRE-P12 neste documento.
- Desabilitar validação TLS, usar `verify=False`, TOFU, degradação HTTPS→HTTP ou fallback de rede após `TLS_ERROR`.
- Autenticar todos os fabricantes, testar credenciais em adapters distintos, trocar família após rejeição, ou exceder D03.
- Criar endpoint proprietário especulativo, alterar roadmap/adapters suportados, inserir autenticação secundária para firmware/dados complementares, ou redefinir campos/status de `CameraResult`.
- Alegar suporte universal, implementação concluída, homologação real validada ou aprovação da presente proposta sem evidência/decisão correspondente.

## 9. Decisões e pontos condicionais

- A direção híbrida e suas invariantes de P2/PRE-P12 são tratadas como aprovadas pelas fontes citadas; esta proposta não as reaprova nem expande.
- **DECISÃO PROPOSTA — hint SINGLE:** adicionar entrada opcional de fabricante. Vazia, preserva os três campos obrigatórios históricos IP/username/password; preenchida, segue exatamente as regras de hint MULTI (`DECLARED`, orientação de roteamento, nunca prova). Pendente de aprovação deste contrato; não reabre P1.
- **DECISÃO PROPOSTA — diagnóstico MULTI:** criar a aba `DIAGNOSTICOS` no XLSX de saída com as colunas e a ordenação definidas na seção 6, sem mudar o inventário/aba existente nem os 14 campos de `CameraResult`. Pendente de aprovação deste contrato.
- A ocorrência concreta na homologação real permanece sem confirmação por log neste checkout; deve ser validada com evidência READ_ONLY apropriada antes de declarar sua abrangência operacional.

```text
ROOT_CAUSE_FROM_CODE = PREAUTH_ONVIF_UNCONDITIONAL_BEFORE_HINT_AND_REGISTRY
TLS_FAIL_CLOSED = REQUIRED_AND_RETAINED
MULTI_ATTEMPT_VISIBILITY = REQUIRED_PROPOSED
SINGLE_OPTIONAL_HINT = PROPOSED_PENDING_APPROVAL
MULTI_DIAGNOSTICS_SHEET = PROPOSED_PENDING_APPROVAL
CANONICAL_CONTRACT_CHANGES = NONE
IMPLEMENTATION_STATUS = NOT_ASSESSED
OPERATIONAL_HOMOLOGATION = NOT_ASSESSED_BY_THIS_DOCUMENT
```
