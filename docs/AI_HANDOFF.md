# AI handoff — SpeedTV Box

Última revisão: 2026-11-13  
Branch de trabalho: `codex/speedtvbox-overhaul`  
Versão do agente nesta branch: 8

## Objetivo

Manter uma página React que gera um agente Python/ADB personalizado para TV Boxes Android. O usuário informa o IP da caixa e a chave Gemini na página; os valores são inseridos no `public/speedtvbox.py` apenas no arquivo baixado. Não colocar chaves reais no repositório.

## Arquitetura

- `src/components/nexo-console.tsx`: página, formulário de IP/chave, download/cópia do agente e tutorial.
- `public/speedtvbox.py`: agente Python, menu CLI, ADB, auditoria, debloat em ondas, reversão, Gemini e relatórios.
- `README.md`: instalação, uso, segurança e testes.
- `docs/AI_HANDOFF.md`: este documento de continuidade.
- `.github/workflows/validate-agent.yml`: validação Python automatizada.

## Mudanças implementadas nesta branch

### Agente Python

- Atualizada versão para 8.
- Incluídos indicadores XCPE conhecidos no inventário: `com.abc.nexus`, `com.android.system.ntp`, `com.android.sso.auth.handler` e `com.ota.service`, além de `x.cpe` e `com.oemservice`.
- A seleção automática por substrings genéricas como `ota` e `recommend` foi removida da onda 2. Agora só entram nomes explicitamente conhecidos.
- A limpeza profunda não oferece mais remoção em massa de pacotes de sistema desconhecidos. Hardware de TV Box usa serviços proprietários que não podem ser classificados só pelo nome.
- O journal registra o estado de ativação anterior do pacote. A reversão tenta restaurar o estado padrão quando ele era `enabled=0`, ou manter habilitado quando era `enabled=1`, além de reinstalar o pacote para o usuário quando necessário.
- O script de rollback inclui `pm install-existing` antes de restaurar o estado do pacote.
- Corrigidos rótulos de onda extra que eram strings e acabavam interpolados com `%d`, provocando `TypeError`.
- Ajustadas as descrições de RAM: MemFree e memória disponível são exibidas separadamente; MemAvailable (ou livre + cache em kernels antigos) é a referência de disponibilidade.
- Removidas alterações automáticas de DNS privado, política de sono do Wi-Fi e varredura BLE. A onda 4 não força resolução 1080p. O DNS e a resolução permanecem como o usuário configurou.
- Adicionado relatório offline `relatorio.html` com gráficos e tabela por etapa, além de `relatorio.json` com snapshots de dispositivo, inventário de pacotes, métricas e ações.

### Página React

- Validação de IPv4 agora verifica os quatro octetos e porta 1–65535.
- Validação da chave Gemini aceita caracteres comuns de API key e evita aspas/quebras de linha.
- Campo da chave usa password.
- Opção explícita para lembrar a chave no navegador; sem a opção, a chave é removida do armazenamento local após o download.
- Revogação da Blob URL é atrasada para não interromper downloads em alguns navegadores.
- Tutorial não recomenda reset de fábrica como pré-requisito; explica que reset apaga dados e não remove malware persistente na firmware.
- A página continua inserindo IP e chave no arquivo Python baixado. Não remover essa integração.

### Documentação e validação

- README reescrito para refletir a versão 8 e as medidas de segurança.
- Workflow de CI executa compilação Python, `selftest` (incluindo geração HTML/JSON), TypeScript, ESLint e build Vite.
- O `package-lock.json` foi sincronizado com `package.json` durante a validação automatizada.

## Regras de segurança

1. Nunca colocar API keys, tokens ou segredos em commits, relatórios, exemplos ou logs.
2. Gemini pode classificar e explicar; não executar comandos shell arbitrários devolvidos pelo modelo. Toda ação deve passar por lista permitida e validação local.
3. Não desativar pacotes de sistema desconhecidos em lote.
4. Proteger sempre SystemUI, Settings, Play/GMS, WebView/Trichrome, launcher ativo, teclado, Bluetooth, Wi-Fi, HDMI, TV input, codec/DRM e componentes de instalação/permissões.
5. Salvar o estado anterior antes de qualquer alteração reversível.
6. Não alegar que uma TV Box está livre de malware só porque nenhum IOC conhecido foi encontrado.
7. Não prometer ganho de RAM: medir antes/depois sob condições comparáveis.
8. Não modificar DNS, resolução de vídeo, Wi-Fi ou Bluetooth sem escolha explícita do usuário.
9. Não confundir `pm uninstall --user 0` com apagar APK da partição do sistema. A operação deve continuar reversível por `install-existing`.

## Testes e status

- **Aprovados no GitHub Actions (run 8):** `python -m py_compile`, `python public/speedtvbox.py selftest` (incluindo geração HTML/JSON), `npm run typecheck`, `npm run lint` e `npm run build:dev`.
- O primeiro CI encontrou o `package-lock.json` fora de sincronia com `package.json`; a instalação foi corrigida e o lockfile foi atualizado na branch.
- Ainda falta validar o relatório HTML em um Android/Termux real e testar rollback em ao menos um Android TV 10/11 e um Android TV 12+.
- Ainda falta testar os comandos de Package Manager em ROMs Amlogic, Rockchip e Allwinner; diferenças de fabricante podem existir.
- O agente ainda precisa de testes unitários com ADB simulado para rollback, pacotes ausentes e respostas de `pm` não padronizadas.

## Próximos passos recomendados

1. Conferir o workflow Python e corrigir qualquer falha antes de merge.
2. Adicionar CI para `npm run typecheck`, `npm run lint` e `npm run build` quando as dependências e o ambiente do projeto estiverem disponíveis.
3. Criar fixtures de saída ADB de Android 10/11/12/13/14/15 e validar os parsers.
4. Testar relatório HTML com valores ausentes, caracteres especiais, inventários grandes e sem permissão de armazenamento compartilhado.
5. Implementar uma confirmação individual e explicação de risco para qualquer pacote proprietário não reconhecido, sem automatizar a remoção.
6. Revisar as regras de proteção para cada SoC e fabricante com evidência, não por suposição.

## Histórico da branch

- 2026-11-13: branch criada para o overhaul; agente v8, rollback, seleção de pacotes, ajustes conservadores, relatório HTML/JSON, validação da página e documentação atualizados.
