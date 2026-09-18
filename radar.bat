@echo off
REM Atalho para rodar o radar sem precisar ativar o venv antes.
REM
REM O comando `radar` so existe no PATH quando o ambiente virtual esta
REM ativado - sem isso o cmd responde "nao e reconhecido como um comando
REM interno ou externo". Este arquivo chama o executavel pelo caminho
REM completo, entao `radar web` funciona de dentro da pasta do projeto de
REM qualquer jeito.
REM
REM %~dp0 e a pasta onde este .bat esta; %* repassa todos os argumentos.

if not exist "%~dp0.venv\Scripts\radar.exe" (
    echo.
    echo O ambiente virtual ainda nao foi criado nesta maquina.
    echo Rode, uma vez, dentro da pasta do projeto:
    echo.
    echo     python -m venv .venv
    echo     .venv\Scripts\activate
    echo     pip install -e ".[dev]"
    echo.
    exit /b 1
)

"%~dp0.venv\Scripts\radar.exe" %*
