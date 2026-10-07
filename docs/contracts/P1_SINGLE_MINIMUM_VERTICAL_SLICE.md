# P1 — SINGLE Minimum Vertical Slice Implementation Contract

```text
PROJECT = projeto_cam_scanner
PHASE = P1
CAPABILITY = SINGLE Minimum Vertical Slice
STATUS = APPROVED_FOR_IMPLEMENTATION
CAMERA_RESULT_CONTRACT_DECISION = APPROVED
CAMERA_RESULT_FIELD_COUNT = 14
P1_IMPLEMENTATION_AUTHORIZATION = GRANTED_FOR_P1_A01
```

## 1. Objetivo e autoridade

Definir o contrato implementável da primeira slice integrada do modo SINGLE: iniciar a aplicação pelo entrypoint canônico, consultar uma câmera real por ONVIF somente leitura, normalizar e apresentar o resultado no terminal e devolver a navegação ao `ApplicationController`.

Este contrato deriva da Engineering Foundation aprovada, da [roadmap](../continuity/planning/ROADMAP.md), do [execution plan](../continuity/planning/EXECUTION_PLAN.md) e dos contratos estruturais já presentes no projeto. O usuário aprovou este contrato e concedeu autorização explícita para a atividade P1-A01 por meio do payload executor de 2026-10-07. Isso não reabre a Foundation nem altera a arquitetura aprovada.

## 2. Fluxo canônico

```text
CLI entrypoint
→ ApplicationController
→ Main Menu
→ SingleWorkflow
→ TerminalUI input
→ CameraTarget
→ InventoryService
→ CameraCollector
→ Generic ONVIF collector
→ GetDeviceInformation
→ CameraResult
→ TerminalUI output
→ post-query navigation action
→ ApplicationController
```

O `ApplicationController` controla navegação e ciclo da aplicação. `SingleWorkflow` não chama `MultiWorkflow`; sua saída de navegação retorna ao controller. A opção MULTI pode ser encaminhada conforme a arquitetura existente, sem implementar MULTI funcional nem antecipar P4.

## 3. Entrada e proteção de credenciais

SINGLE solicita IP, username e password no terminal. A senha é obrigatoriamente lida por `getpass()` e mantida apenas em memória durante a coleta. `CameraTarget.password` preserva `repr=False`.

A senha não pode aparecer em `CameraResult`, terminal, logs, exceptions sanitizadas, telemetry ou arquivos temporários. Erros e logs devem ser sanitizados antes de exposição. O username não deve ser registrado por padrão, conforme EF-LOGGING-01.

## 4. Consulta ONVIF mínima

Executar uma consulta real, estritamente READ_ONLY, pelo collector ONVIF genérico. A operação mínima é `GetDeviceInformation`. Coletar quando a câmera retornar: Manufacturer, Model, SerialNumber e FirmwareVersion.

Não fazem parte de P1: inventário de rede completo, DHCP, máscara, gateway, DNS, portas, enriquecimento específico de fabricante, adapters proprietários, snapshot, RTSP ou XLSX.

O fluxo não pode expor ou chamar operações de alteração da câmera, incluindo `set_*`, reboot, firmware update, factory reset, gravação de configuração, alteração de credenciais, alteração de rede, alteração de horário ou equivalentes. Usar somente operações necessárias de leitura.

## 5. Resultado normalizado e compatibilidade estrutural

O `CameraResult` mantém seus dez campos existentes e acrescenta exclusivamente os quatro campos tipados aprovados pelo usuário nesta reconciliação. O total resultante é 14 campos:

```text
ip, status, hostname, manufacturer, manufacturer_original,
model, serial, firmware, hardware_id, mac,
error_code, error_message, collection_method, duration
```

Os dez campos existentes são preservados. `error_code`, `error_message`, `collection_method` e `duration` são os únicos campos novos. Nenhuma senha ou extension bag arbitrário é permitido; são proibidos `metadata`, `extra`, `extras`, `payload`, `context`, `raw_data`, `attributes`, `custom` ou equivalente. Para esta slice, preencher no mínimo `ip`, `status`, `manufacturer`, `model`, `serial` e `firmware`; mapear SerialNumber para `serial` e FirmwareVersion para `firmware`. Campos não fornecidos pela câmera permanecem ausentes conforme os tipos opcionais existentes. Não inventar semântica nova para `CollectionStatus`; P1 requer ao menos `SUCCESS` e `FAILED` dentre os estados já definidos.

### Contrato canônico de tipagem

As decisões abaixo foram aprovadas pelo usuário em P1-C01-R2 e fecham as pendências de tipagem sem alterar a contagem de campos ou autorizar implementação:

| Campo | Tipo canônico | Regras |
|---|---|---|
| `error_code` | `ErrorCode | None` | `SUCCESS` → `None`; `FAILED` → obrigatório. Vocabulário P1: `INVALID_INPUT`, `NETWORK_ERROR`, `TIMEOUT`, `AUTH_ERROR`, `ONVIF_ERROR`, `UNEXPECTED_ERROR`. |
| `error_message` | `str | None` | `SUCCESS` → `None`; `FAILED` → obrigatório. Mensagem sanitizada, sem traceback, password ou URL com credenciais. |
| `collection_method` | `CollectionMethod | None` | Vocabulário P1: `ONVIF`. `ONVIF` quando uma tentativa ONVIF efetivamente iniciar; `None` se a falha ocorrer antes de qualquer tentativa de coleta. |
| `duration` | `float` | Segundos, não nullable, medido com relógio monotônico; deve ser finito e maior ou igual a zero. |

Os vocabulários de `ErrorCode` e `CollectionMethod` só podem ser estendidos quando uma fase posterior introduzir capability que exija novo valor. Não antecipar valores de snapshot, RTSP, vendor adapters, XLSX, MULTI, cancelamento ou packaging nesta atividade. `CollectionStatus` existente é reutilizado; não criar status concorrente.

O `CameraResult` contém exatamente os dez campos existentes e os quatro campos acima (14). Nenhuma senha ou extension bag arbitrário é permitido; são proibidos `metadata`, `extra`, `extras`, `payload`, `context`, `raw_data`, `attributes`, `custom` ou equivalente.

## 6. Collection method

O método de coleta da operação P1 usa o tipo `CollectionMethod | None`, com vocabulário P1 `ONVIF` e regras definidas na seção 5. Nenhum vendor adapter pertence a P1.

## 7. Erros e continuidade da aplicação

Erros esperados não encerram a aplicação nem mostram traceback ao operador. Cobrir `INVALID_INPUT`, `NETWORK_ERROR`/timeout, `AUTH_ERROR`, `ONVIF_ERROR` e `UNEXPECTED_ERROR` sanitizado. Após falha de consulta SINGLE, produzir resultado compatível com o contrato aprovado, exibir mensagem legível, manter a aplicação operacional e oferecer o menu pós-consulta.

Terminal recebe mensagem sanitizada. Para exception inesperada, o log pode receber stack trace sanitizado conforme EF-LOGGING-01; nenhum segredo pode ser incluído. `error_code` e `error_message` seguem os tipos e regras da seção 5.

## 8. Menu pós-consulta

Após consulta concluída, com sucesso ou falha esperada, apresentar:

```text
[1] Pesquisar outra câmera
[2] Ir para modo MULTI
[3] Sair
```

`SingleWorkflow` devolve uma navigation action para `ApplicationController`. A opção 2 apenas entrega a navegação ao controller conforme arquitetura existente; não implementa MULTI funcional nesta fase.

## 9. Escopo

**Incluído:** bootstrap do fluxo, menu principal, SINGLE, entrada terminal e `getpass()`, `CameraTarget`, `ApplicationController`, `SingleWorkflow`, `InventoryService`, `CameraCollector`, ONVIF genérico, `GetDeviceInformation`, resultado normalizado, saída terminal, erros esperados, navegação pós-consulta, testes da slice e integração canônica.

**Excluído:** snapshot, XLSX, MULTI funcional, concorrência/`ThreadPoolExecutor`, vendor adapters (Axis, Hikvision, Samsung/Hanwha, Dahua, Panasonic, Bosch), RTSP, PyAV, packaging, PyInstaller, instalação/release e expansão do inventário de rede.

## 10. Contrato de integração

P1 somente será considerada implementada quando o caminho real `CLI entrypoint → menu → SINGLE → ONVIF → CameraResult → terminal → navigation` estiver integrado. `IMPLEMENTED != INTEGRATED` e `UNIT_TEST_PASS != P1_DONE`. Não acumular módulos desconectados para integrar no final.

## 11. Critérios de aceite

| ID | Critério |
|---|---|
| AC-01 | Aplicação inicia pelo entrypoint canônico. |
| AC-02 | Menu principal oferece SINGLE, MULTI e Sair. |
| AC-03 | SINGLE solicita IP, username e password por `getpass()`. |
| AC-04 | `CameraTarget` é criado sem expor a senha. |
| AC-05 | Consulta ONVIF real e READ_ONLY é executada. |
| AC-06 | Manufacturer, Model, SerialNumber e FirmwareVersion são coletados quando disponíveis. |
| AC-07 | `CameraResult` contém exatamente os dez campos preservados e os quatro campos novos aprovados; sem password ou extension bag arbitrário. |
| AC-08 | Resultado é apresentado no terminal. |
| AC-09 | Falha de autenticação não mostra traceback no terminal. |
| AC-10 | Timeout/rede não encerram a aplicação. |
| AC-11 | Menu pós-consulta funciona. |
| AC-12 | `SingleWorkflow` não chama `MultiWorkflow` diretamente. |
| AC-13 | Nenhuma operação mutante de câmera é introduzida. |
| AC-14 | Nenhuma senha aparece em output, log ou resultado. |
| AC-15 | Fluxo integrado é demonstrado em Python 3.14.x. |

## 12. Validação da implementação futura

Após autorização de implementação, validar proporcionalmente com: testes unitários aplicáveis; testes estruturais; testes de `ApplicationController`, `SingleWorkflow` e `CameraResult`; testes de sanitização/segurança; fake/mock ONVIF determinístico; teste integrado do fluxo CLI quando tecnicamente viável; evidência operacional por consulta real à câmera; Ruff; pytest; e Python 3.14.x. A indisponibilidade atual de pytest/Ruff deve ser tratada no preflight adequado da implementação, não ocultada. Não instalar dependências durante P1-C01.

## 13. Definition of Done de P1

P1 só será DONE após código implementado; módulos validados; integração canônica realizada e validada; regressão aplicável PASS; consulta real READ_ONLY demonstrada; Python 3.14.x validado; nenhuma senha vazada; nenhum traceback esperado no terminal; nenhuma funcionalidade fora de P1 introduzida; `PROJECT_STATE` reconciliado; e handoff PASS. A divergência pendente da seção 5 deve estar decidida antes da implementação.

## 14. Limite de implementação e continuidade

```text
P1_CONTRACT_STATUS = APPROVED
P1_IMPLEMENTATION_AUTHORIZATION = GRANTED_FOR_P1_A01
NEXT_ACTIVITY = P1-A01 synthetic validation and authorized real-camera validation
FIELD_COUNT = 14
ARBITRARY_EXTENSION_BAG = PROHIBITED
PASSWORD_FIELD = PROHIBITED
TYPING_DECISIONS_PENDING = NONE
```

Este contrato registra os limites e as decisões aprovadas pelo usuário. A autorização concede somente a implementação e validação de P1-A01; não autoriza alteração da Foundation nem escrita Git, commit, push, tag ou release.
