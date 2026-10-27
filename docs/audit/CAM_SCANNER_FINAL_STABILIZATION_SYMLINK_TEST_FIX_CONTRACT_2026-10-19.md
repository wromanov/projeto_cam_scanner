# Contrato de correção do teste de symlink — estabilização final

**Projeto:** `projeto_cam_scanner`  
**Atividade:** `CAM_SCANNER_FINAL_STABILIZATION`  
**Data:** 2026-10-19  
**Estado:** contrato decidido; implementação e validação pendentes

## Fatos e evidências

- O teste `tests/test_logging_setup.py::test_windows_filesystem_retention_never_follows_real_symlink` cria um symlink real no Windows e, em seguida, falha ao chamar `os.utime(link, ..., follow_symlinks=False)`, com `NotImplementedError` no ambiente testado.
- A falha ocorre na preparação do teste, antes da chamada de retenção que ele pretende verificar. A evidência disponível não demonstra defeito em `src/cam_scanner/logging/setup.py`.
- O teste trata WinError 1314 ao criar o symlink como `SKIP` explícito. Esse resultado não equivale a PASS e não satisfaz o aceite do Gate V.

## Decisão

Alterar somente o teste `test_windows_filesystem_retention_never_follows_real_symlink`, em `tests/test_logging_setup.py`. Não alterar código de produção sem evidência posterior de defeito real.

Remover a chamada a `os.utime` sobre o próprio symlink com `follow_symlinks=False`. Após criar o symlink, avançar em 40 dias apenas o relógio usado por `cam_scanner.logging.setup`, aplicando `monkeypatch.setattr(logging_setup, "datetime", FutureDateTime)`. O `FutureDateTime.now(cls, tz=None)` deve calcular a base com `real_datetime.now(UTC) + timedelta(days=40)`, devolver o instante no fuso solicitado e, quando `tz=None`, devolver a hora local sem informação de fuso.

Envelhecer com `os.utime(path, ...)` comum tanto o alvo quanto um arquivo regular vencido cujo nome corresponda ao padrão de log do produto. O relógio adiantado também pode participar da geração do nome do novo log durante `configure_logging`; isso é aceitável para este teste.

## Invariantes da implementação

1. O teste continua exercitando um symlink real no Windows.
2. Nenhuma operação de preparação altera o mtime do reparse point do symlink.
3. Antes de configurar o logging, `link.lstat()` confirma que a entrada é um symlink e que seu mtime está abaixo do cutoff calculado com o relógio adiantado.
4. Depois de `configure_logging()`, o arquivo regular vencido foi removido; o link continua sendo symlink e existe; o conteúdo do alvo permanece inalterado.
5. `close_logging()` é executado em `finally`.
6. WinError 1314 continua sendo registrado como `SKIP` explícito, sem ser mascarado ou convertido em PASS.

## Critérios de aceite

O teste focal precisa passar em execução real no Windows com Python 3.14, criando symlink real e verificando todas as pré-condições e pós-condições acima, sem `SKIP` e sem `NotImplementedError`.

Somente após esse PASS focal deve ser executada a regressão completa. Gate 2 e Gate V requerem regressão sem falhas, skips ou testes desmarcados. Gate 3 permanece condicionado à revisão independente dos findings; este teste não promove Gate 3 por si só. P12 não deve ser gerado antes de Gate V PASS.

Se houver WinError 1314 com `SKIP`, falha do teste ou outra incompatibilidade, os gates permanecem abertos; o resultado deve ser registrado sem mascaramento.

## Risco registrado

O relógio adiantado pode fazer o nome do novo log criado pelo teste conter um timestamp futuro. Isso é um efeito de preparação do teste e não altera a semântica de retenção avaliada.

## Estado de validação

Este documento registra o contrato de correção. Não afirma que a implementação foi realizada, que o teste passou, que a regressão foi executada ou que qualquer gate foi concluído.
