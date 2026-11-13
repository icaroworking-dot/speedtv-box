# SpeedTV Box

Página que monta o agente de TV Box. A pessoa informa o IP da TV Box e a chave do Gemini; o arquivo `speedtvbox.py` baixado já recebe os dois valores. **A chave não é gravada no repositório.** O navegador só a mantém entre visitas se a opção “Lembrar a chave neste navegador” estiver marcada.

## Usar no Android / Termux

1. Instale o Termux por uma fonte mantida (por exemplo, F-Droid).
2. No Termux, rode:

```bash
pkg update
pkg install python android-tools
termux-setup-storage
```

3. Baixe o `speedtvbox.py` personalizado na página e permita o acesso aos arquivos.
4. Rode o bloco abaixo no Termux:

```bash
f=$(find "$HOME/storage/downloads" "$HOME/storage/shared/Download" "$HOME/storage/shared/Downloads" -iname 'speedtvbox.py*' 2>/dev/null | head -n 1)
echo "Achei: ${f:-nada}"
cp "$f" "$HOME/speedtvbox.py"
cd "$HOME"
python speedtvbox.py
```

Na primeira execução, escolha **1 — Começar agora**. Não é necessário resetar a TV Box para fazer a auditoria. O agente lê primeiro e pergunta antes das ações de limpeza. Faça backup dos dados importantes.

## O que o agente faz

- Identifica modelo, fabricante, SoC/placa, ABI, Android/SDK, kernel, patch, memória física estimada, armazenamento, ZRAM, Widevine e inventário de pacotes.
- Mede RAM disponível, processos, pacotes desativados e armazenamento antes/depois de cada onda.
- Usa listas de proteção, identifica launcher/teclado/serviços ativos e evita remoção em massa de pacotes de sistema desconhecidos.
- Detecta indicadores conhecidos de Adups/XCPE e outros pacotes suspeitos. Isso não é garantia de que o firmware esteja limpo.
- Registra o estado anterior dos pacotes e oferece reversão; gera script de recuperação.
- Gera TXT, JSON e um relatório HTML offline com gráficos e métricas por etapa.
- Preserva a integração Gemini: a página injeta a chave e o IP no arquivo Python baixado; o agente usa o Gemini como apoio, sem executar comandos arbitrários retornados pelo modelo.

## Segurança e compatibilidade

- O debloat usa comandos de Package Manager limitados ao usuário Android atual; não apaga arquivos da partição `/system`.
- A seleção de pacotes desconhecidos é conservadora. Não confirme pacotes de sistema que você não reconheça.
- DNS privado, Bluetooth, parâmetros de Wi-Fi e resolução de vídeo não são alterados automaticamente.
- A resolução pode ser avaliada e alterada separadamente quando o usuário decidir.
- A contagem de processos é aproximada. MemAvailable (ou livre + cache em kernels antigos) é mais útil que MemFree isolado.
- Um reset de fábrica não remove malware embutido na firmware.

## Relatórios

Os arquivos ficam em `Download/SpeedTV` quando o Termux tem permissão de armazenamento; caso contrário, ficam em `$HOME/speedtv-dados`. O HTML abre localmente e não depende de CDN.

## Testes

```bash
python -m py_compile public/speedtvbox.py
python public/speedtvbox.py selftest
```

## Publicação

A página pode ser publicada pela Vercel ligada ao repositório. O download do agente é servido por `public/speedtvbox.py`. Quem já baixou um agente precisa baixar novamente para receber as correções.
