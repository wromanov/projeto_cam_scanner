# ASTRA — Registro P2: decisões de mídia diferidas

```text
PROJECT_ID = projeto_cam_scanner
ACTIVITY_ID = CAM_SCANNER_ASTRA_CONTRACT_CLOSURE_01
RECORD_ID = ASTRA_P2_MEDIA_DEFERRED_V1
PARENT_ACTIVITY = CAM_SCANNER_ASTRA_FEASIBILITY_AUDIT_01
DECISION_STATUS = DEFERRED
RECORD_STATUS = READY_FOR_USER_REVIEW
IMPLEMENTATION_CONTRACT = NONE
IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED
REAL_CAMERA_ACCESS = NOT_AUTHORIZED
RTSP_CAPTURE_AUTHORIZATION = NOT_GRANTED
```

P2 aqui é prioridade do adendo, não alteração da fase histórica P2. Este registro documenta limites e evidência futura; não contém algoritmo, backlog técnico executável ou autorização para implementar mídia. A direção de adiar estas decisões vem do Card do usuário de 27/10/2026.

## 1. Contexto e fundamento

A auditoria original F07 constatou RTSP desabilitado na produção (`src/cam_scanner/snapshot/rtsp.py:29,47–52`), snapshot proprietário limitado à família Hikvision KD8003 (`snapshot/manufacturer.py:24,49–57`) e necessidade de escopo já aceito para imagem (`snapshot/service.py:115–145`). Isso é cobertura limitada do app, não prova de incapacidade de uma conta viewer obter vídeo em outro cliente.

O [contrato P0](ASTRA_P0_REQUIRED_CORRECTIONS_IMPLEMENTATION_CONTRACT.md) registra a baseline R2 suja e F01–F09; o [P1](ASTRA_P1_COVERAGE_IMPROVEMENTS_IMPLEMENTATION_CONTRACT.md) trata entrada/modelo e campos já recebidos. O [PRE-P12 histórico](PRE_P12_UNIFIED_REMEDIATION_CONTRACT.md), §§6–8, continua impondo destinos, TLS, auth, budget e cancelamento. Não se propõe reescrita integral do transporte.

## 2. Decisões diferidas e condições de desbloqueio

| ID | Decisão | Motivo e risco | Pré-condições e evidência necessária | Decisão futura requerida |
|---|---|---|---|---|
| ASTRA-P2-D01 | Ampliação de snapshots proprietários — DEFERRED | Depende de endpoint/canal/modelo e permissão viewer; aumenta escopo de credencial e cobertura a manter | Documentação oficial específica, modelo/firmware/canal, semântica estritamente de leitura; permissão de conta existente; negativos de auth/TLS/destino e preservação de identidade | Aprovar escopo por família e contrato específico, depois autorizar implementação offline |
| ASTRA-P2-D02 | Captura RTSP em produção — DEFERRED | Decoder pode abrir redirects, SDP/control URLs, portas e conexões auxiliares fora do destino inicial validado; timeout/cancelamento e auth não são equivalentes a Requests | Evidência de todos os destinos antes de abrir conexão, decoder/biblioteca suportados, sem URIs com credenciais; limites de quadro/dimensões/recursos/concorrência, close em sucesso/falha/cancelamento e testes de desvio de destino | Aprovar arquitetura de confinamento e contrato de implementação/revisão de segurança; depois autorização própria para eventual habilitação |
| ASTRA-P2-D03 | Novos endpoints de imagem — DEFERRED | URL plausível ou acesso a live view não prova API/canal suportado; métodos GET podem alterar estado | Fonte primária, operação/params/canal documentados, requests mínimos, ACL por operação, nenhuma varredura ou tentativa por vários vendors | Aprovar lista restrita de operações e modelos, sem generalização por similaridade |
| ASTRA-P2-D04 | Alteração de autorização para mídia — DEFERRED | Identidade bem-sucedida em um serviço não autoriza login em outro; risco de repetir credenciais após recusa e violar D03 | Prova de escopo de usuário/serviço já existente, mecanismo de auth, finalidade/budget, precedência de recusas e revisão de limites; não criar contas ou elevar papéis | Decisão normativa expressa antes de qualquer alteração de ledger/fallback para imagem |

Firmware, papéis e serviço já precisam existir no equipamento. Uma pré-condição que só possa ser satisfeita habilitando serviço, alterando câmera/usuário/certificado/firmware ou reboot não é plano de desbloqueio permitido; nesse alvo, a funcionalidade permanece indisponível.

## 3. O que permanece preservado

- Não alterar `_RTSP_CAPTURE_ENABLED = False`, inclusive como “teste temporário” de produto nesta atividade ou nos contratos P0/P1.
- Não acrescentar providers/endpoints de snapshot ou novos fallbacks autenticados.
- Imagem é opcional perante IDENTITY_V1; ausência/falha não apaga modelo, serial, fabricante e outras evidências válidas.
- TLS_ERROR fecha rede; 401 final/403 fecha novas autenticações; sessão HTTPS aceita não autoriza RTSP. Não interpretar PARTIAL_SUCCESS como permissão para imagem.
- Nenhuma mudança de transporte/credencial/porta/destino implícita. HTTP continua por alvo/componente/porta previamente autorizados, sem downgrade.
- Fluxos de captura atuais continuam sujeitos aos limites de PRE-P12; este registro não amplia seu funcionamento.
- Não executar testes Set/escrita, nem testes negativos dessas operações em câmeras.

## 4. Transporte, autenticação e capabilities

HTTP/HTTPS são transporte; Digest/Basic/WSSE são mecanismos distintos. Uma URL RTSP não demonstra confidencialidade, permissão ou garantia de confinamento. ONVIF Media, Device Management e API proprietária podem ter escopos de conta diferentes, mesmo com username/senha iguais.

F04 (novos algoritmos ou mecanismos auth para inventário) permanece no gate AUTH-EXT do contrato P0; não é resolvido ou autorizado por adiar mídia. Não incorporar à mídia uma expansão genérica de auth para “fazer funcionar”. Não implementar criptografia própria nem descobrir permissões por tentativas sucessivas.

## 5. Evidência futura mínima e risco operacional residual

Para uma decisão posterior, preparar proposta que liste: operação documentada, família/modelo/firmware, serviço já ativo, conta viewer existente e papel atestado sem segredo, transporte/mecanismo, destinos exatos inclusive auxiliares, operações físicas/lógicas previstas e tempos/budgets. Sem inventar endpoint, payload ou suporte de decoder.

Prova offline futura deve usar componentes reais com transporte/local server controlados; testar redirecionamentos e URLs de controle hostis, cross-target/portas, auth final e challenge, payload/codec/stream inválido, dimensões/tamanho, deadline/cancelamento e encerramento. Não extrair da presença de código PyAV uma capacidade produtiva habilitada.

Prova física futura exige autorização operacional separada para alvos e leituras exatos, sem reconfigurar câmeras. Deve registrar somente resultados sanitizados, campos/imagem autorizados e contagens, nunca senha/header/body bruto. Não gerar carga de streaming em massa. Se não houver serviço/conta permissível já existente, registrar NOT_VERIFIED ou UNSUPPORTED conforme evidência, sem intervenção.

## 6. Gates de decisão, sem plano executável

Não há ordem de implementação, critérios de DONE de código ou AC de produto neste registro. Há condições para apreciação futura:

1. G-MEDIA-EVIDENCE: documentação e necessidade de produto comprovadas para o escopo.
2. G-MEDIA-SECURITY: confinamento de destinos/auth/recursos e revisão técnica antes da habilitação.
3. G-MEDIA-NORMATIVE: usuário decide alterações de operações, escopo de mídia e relação com D03/PRE-P12.
4. G-MEDIA-IMPLEMENTATION: contrato novo, revisável e aprovado, seguido de autorização offline própria.
5. G-MEDIA-OPERATIONAL: autorização física específica e homologação READ_ONLY sem alterações de parque.

Esses gates não são concedidos por aprovação dos contratos P0/P1, por este registro ou pelo build histórico. Não selecionar método de confinamento, codec, endpoint ou biblioteca neste documento.

## 7. Situações que mantêm o adiamento

Destinos auxiliares não controláveis; segredo exigido em URI/log; necessidade de novos usuários/serviços; decoder sem cancelamento/limites apropriados; ausência de documentação/role; ampliação de HTTP para rede inteira; necessidade de desativar TLS; tentativa de autenticação após recusa final; falta de autoridade operacional. Reportar a condição exata sem contorná-la.

## 8. Rastreabilidade e revisão documental

| Finding/autoridade | Relação | Status |
|---|---|---|
| F07 | Cobertura atual de imagem reduzida | DEFERRED, não CLEARED |
| F03 | Prova operacional viewer ausente | Continua NOT_VERIFIED; fixtures de mídia não a substituem |
| F04 / AUTH-EXT | Mecanismos/algoritmos de auth | Fora de P0/P1 executável; decisão separada |
| P0/P1 deste adendo | Inventário e campos disponíveis | Independentes de habilitar RTSP ou ampliar imagem |
| PRE-P12 / D03 | Segurança de destinos/TLS/auth/deadline | PRESERVED; nenhuma mudança normativa neste registro |

Validação desta autoria: conferir existência dos quatro registros D01–D04, razões, riscos, pré-condições, evidências e decisão requerida; links aos contratos; linguagem DEFERRED e ausência de autorização/algoritmo executável. Essa revisão documental não realiza testes de mídia.

## 9. Status e próxima decisão

P2_DECISION_STATUS=DEFERRED. Aprovação futura de uma ideia de mídia não substitui contrato e autorização executável próprios. A próxima decisão atual do usuário se restringe aos contratos P0/P1 propostos; mídia permanece adiada e seu bloqueio de produção preservado.
