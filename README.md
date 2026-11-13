# SpeedTV Box

Página que monta o agente de TV Box. A pessoa informa o IP da TV Box e a chave do Gemini; o arquivo `speedtvbox.py` é personalizado no próprio navegador. **A chave não é enviada ao servidor nem gravada no repositório.** O navegador só a mantém entre visitas se a opção “Lembrar a chave neste navegador” estiver marcada. O arquivo gerado contém a chave: não o publique nem compartilhe.

## Usar no Android / Termux

1. Instale o Termux por uma fonte mantida (por exemplo, F-Droid).
2. No Termux, rode:

```bash
pkg update
pkg install python android-tools
termux-setup-storage
```

3. Na página, toque em **Gerar .py** e depois no link **Salvar .py**. Permita o acesso aos arquivos.
4. Rode o bloco abaixo no Termux:

```bash
f=$(find "$HOME/storage/downloads" "$HOME/storage/shared/Download" "$HOME/storage/shared/Downloads" -iname 'speedtvbox.py*' 2>/dev/null | head -n 1)
echo "Achei: ${f:-nada}"
cp "$f" "$HOME/speedtvbox.py"
cd "$HOME"
python speedtvbox.py
```

Na primeira execução, escolha **1 — Começar**. O assistente conduz a auditoria, identifica o aparelho, verifica riscos, apresenta os grupos de limpeza e pergunta antes das ações. Não é necessário resetar a TV Box para começar. Faça backup dos dados importantes.

## O que o agente faz

- Identifica modelo, fabricante, SoC/placa, ABI, Android/SDK, kernel, patch, memória física estimada, armazenamento, ZRAM, Widevine e inventário de pacotes.
- Mede RAM disponível, processos, pacotes desativados e armazenamento antes/depois de cada onda.
- Usa listas de proteção, identifica launcher/teclado/serviços ativos e evita remoção em massa de pacotes de sistema desconhecidos.
- Detecta indicadores conhecidos de Adups/XCPE e outros pacotes suspeitos. Isso não é garantia de que o firmware esteja limpo.
- Registra o estado anterior dos pacotes e oferece reversão; gera script de recuperação.
- Gera TXT, JSON e um relatório HTML offline com gráficos e métricas por etapa.
- Menu guiado: auditoria, diagnóstico, memória/armazenamento, instaladores, segurança, recuperação e ferramentas.
- Modo sem Google opcional: permite desativar/reativar separadamente GMS, GSF, Play Store e serviços auxiliares. Não desinstala APKs e avisa sobre dependências.
- Diagnóstico de rede para IPTV: Wi-Fi, RSSI/link, interfaces, rotas, DNS e testes básicos de latência/resolução. Não muda DNS, MTU ou rádio automaticamente.
- Auditoria de codecs: lê MediaCodec, player/extractor, placa e saída de vídeo. Não promete adicionar decoders: codecs de hardware dependem do firmware/vendor.
- Diagnóstico da barra lateral/navegação: coleta estado do Projectivy/Glass, HOME e configurações de imersão sem esconder botões nem alterar SystemUI.
- Instala Glass Launcher (`com.fares.glass`) e Projectivy Launcher a partir dos repositórios oficiais dos desenvolvedores; tenta definir HOME, pede teste do botão do controle e só oferece desativar o launcher anterior depois da confirmação. A desativação é reversível.
- Abre a página oficial do Google Play para instalar Downloader by AFTVnews; se a Play Store estiver desativada, pode reativá-la temporariamente com autorização e restaurar o estado anterior depois. A instalação final é confirmada pelo usuário na loja.
- Inclui limpeza de cache pelo Package Manager e fechamento opcional de apps de usuário pesados, sem forçar parada de componentes do sistema.
- Preserva a integração Gemini: a página injeta a chave e o IP no arquivo Python baixado; o agente usa o Gemini como apoio, sem executar comandos arbitrários retornados pelo modelo.

## Segurança e compatibilidade

- O debloat usa comandos de Package Manager limitados ao usuário Android atual; não apaga arquivos da partição `/system`.
- A limpeza foi ampliada com perfis de pacotes exatos conhecidos (incluindo utilitários de fábrica observados em TV Boxes Amlogic/Aquário, Pluto TV e VLC quando presentes). Apps de usuário não entram em ondas automáticas; pacotes desconhecidos não são desativados às cegas. A onda mais profunda continua opcional e exige confirmação.
- DNS privado, Bluetooth, parâmetros de Wi-Fi e resolução de vídeo não são alterados automaticamente. A limpeza de armazenamento usa `pm trim-caches`; não apaga fotos, vídeos, dados de apps ou arquivos de sistema.
- A resolução pode ser avaliada e alterada separadamente quando o usuário decidir.
- A contagem de processos é aproximada. MemAvailable (ou livre + cache em kernels antigos) é mais útil que MemFree isolado.
- A família Android é estimada pelo SDK/API (por exemplo, SDK 25 = Android 7.1); `ro.build.version.release` e kernel são verificações cruzadas. Divergência é alerta, não prova automática de falsificação.
- A ausência de Widevine em `dumpsys` não prova ausência de certificação. Não se deve mexer em bibliotecas DRM para tentar liberar HD.
- A varredura de segurança procura indicadores conhecidos; não é antivírus e não garante firmware limpo.
- Um reset de fábrica não remove malware embutido na firmware.

## Relatórios

Os arquivos ficam em `Download/SpeedTV` quando o Termux tem permissão de armazenamento; caso contrário, ficam em `$HOME/speedtv-dados`. O HTML abre localmente e não depende de CDN.

## Testes

```bash
python -m py_compile public/speedtvbox.py
python public/speedtvbox.py selftest
```

## Publicação

A página pode ser publicada pela Vercel ligada ao repositório. O agente é servido por `public/speedtvbox.py`. O gerador valida o conteúdo recebido, não depende de `localStorage` para funcionar e entrega um link real de salvamento após personalizar o arquivo. Quem já baixou um agente precisa gerar e salvar novamente para receber as correções.
