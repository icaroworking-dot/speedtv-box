import { useEffect, useState } from "react";
import {
  Activity,
  Copy,
  Download,
  Radio,
  RotateCcw,
  Shield,
  Store,
} from "lucide-react";

const FILE = "/speedtvbox.py";

const ONDAS = [
  {
    n: "01",
    nome: "Ler",
    texto:
      "RAM real contra a de vitrine, Android da etiqueta contra o kernel, Widevine, app de fábrica e nome de vírus. Nada é desativado.",
  },
  {
    n: "02",
    nome: "Perguntar",
    texto:
      "Se achar XCPE ou Adups, pergunta se desativa. Se achar Netflix, Kodi, Prime ou Disney de fábrica, pergunta de novo. YouTube da TV fica.",
  },
  {
    n: "03",
    nome: "Limpar",
    texto:
      "Ondas com reinício. Calendário e app de telefone podem sair. Loja, GMS, WebView, launcher, teclado, HDMI e codec não.",
  },
  {
    n: "04",
    nome: "Relatório",
    texto:
      "Um texto em Download/SpeedTV: antes e depois, a lista do que saiu, a RAM verdadeira, o Android verdadeiro e o Widevine.",
  },
];

const MEDIDAS = [
  ["RAM", "meminfo, mapa iomem e dumpsys. Se a prop disser 4 GB e o kernel mostrar menos, o relatório marca vitrine."],
  ["Android", "SDK, release e kernel. Android 14 em kernel 4.4 é mentira de firmware, não é patch velho."],
  ["Widevine", "Lê o nível. L1 de TV Box genérica é vitrine até um filme protegido tocar. Não existe atalho para 4K."],
  ["Ameaça", "Adups, OTA silenciosa e o backdoor XCPE (com.oemservice / x.cpe), que aluga o IP da casa e volta da partição /oem."],
  ["Play", "O que está desativado, escondido ou removido só para o usuário, inclusive WebView e Trichrome."],
  ["Termux", "O relatório vai para Download/SpeedTV, a pasta que abre no app Arquivos."],
];

const COMANDOS = [
  ["python speedtvbox.py", "abre o menu. Na primeira vez, escolha 1"],
  ["python speedtvbox.py primeira", "o mesmo caminho, sem abrir o menu"],
  ["python speedtvbox.py playstore", "só o reparo da loja"],
  ["python speedtvbox.py reverter", "desfaz o que o SpeedTV Box mudou"],
];

const BLOCO_TERMUX = `f=$(find "$HOME/storage/downloads" "$HOME/storage/shared/Download" "$HOME/storage/shared/Downloads" -iname 'speedtvbox.py*' 2>/dev/null | head -n 1)
echo "Achei: \${f:-nada}"
cp "$f" "$HOME/speedtvbox.py"
cd "$HOME"
python speedtvbox.py`;

const PASSOS = [
  {
    n: "01",
    nome: "Preparar a TV Box",
    texto:
      "Reset de fábrica não é obrigatório para começar e apaga contas e aplicativos. Primeiro faça a auditoria. Só use o recovery se você realmente quiser zerar os dados ou se houver um problema que justifique isso; ele não remove malware gravado na firmware.",
  },
  {
    n: "02",
    nome: "Depuração",
    texto:
      "Mesma Wi-Fi do celular. Configurações, Sobre, sete toques em Compilação. Opções do desenvolvedor, Depuração USB. No Android 11 ou mais novo, a depuração sem fio mostra um código. Anote o IP da rede. A porta do dia a dia é 5555. A porta do pareamento é outra, a que está na tela.",
  },
  {
    n: "03",
    nome: "Baixar o agente",
    texto:
      "Nesta página, aba Baixar. Cole o IP e a chave do Gemini. Baixe o .py. A chave fica só nesse arquivo, no seu celular. Não publique esse arquivo.",
  },
  {
    n: "04",
    nome: "Escolher 1",
    texto:
      "No Termux, cole o bloco inteiro. Dentro do agente, escolha 1. O relatório fica em Download/SpeedTV.",
  },
];

function Tutorial() {
  return (
    <div className="mt-8 space-y-8">
      <section className="rounded-2xl border border-line bg-surface p-5 sm:p-6">
        <p className="font-mono text-xs tracking-widest text-amber">PRIMEIRA VEZ</p>
        <h2 className="mt-2 font-display text-4xl leading-none text-fg">Da preparação ao relatório</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
          Não precisa formatar a TV Box para começar. Escolha 1 para auditar, revisar os riscos e decidir o que será desativado. O relatório vai para Download/SpeedTV quando o Android permitir.
        </p>
      </section>

      <section>
        <h2 className="font-display text-3xl text-fg">O que instalar</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-line bg-bg-raised p-5">
            <h3 className="font-display text-2xl text-fg">Celular</h3>
            <ol className="mt-3 space-y-2 text-sm leading-relaxed text-muted">
              <li>Termux pelo F-Droid. A cópia da Play Store está velha e falha.</li>
              <li>
                Uma vez, dentro do Termux:{" "}
                <span className="font-mono text-xs text-fg">pkg update && pkg install python android-tools</span>
              </li>
              <li>
                Depois: <span className="font-mono text-xs text-fg">termux-setup-storage</span> e aceite o acesso aos arquivos.
              </li>
            </ol>
          </article>
          <article className="rounded-2xl border border-line bg-bg-raised p-5">
            <h3 className="font-display text-2xl text-fg">Computador</h3>
            <ol className="mt-3 space-y-2 text-sm leading-relaxed text-muted">
              <li>Python 3, do site python.org.</li>
              <li>Platform-Tools, do site de desenvolvedores Android. Descompacte.</li>
              <li>No Windows, Prompt de Comando. No Mac, Terminal. Os comandos são os mesmos.</li>
              <li>Cabo USB só se a TV Box aceitar depuração por cabo. Wi-Fi basta quando a depuração sem fio está ligada.</li>
            </ol>
          </article>
        </div>
      </section>

      <section>
        <h2 className="font-display text-3xl text-fg">A ordem</h2>
        <ol className="mt-4 divide-y divide-line border-y border-line">
          {PASSOS.map((passo) => (
            <li key={passo.n} className="grid gap-2 py-4 sm:grid-cols-12 sm:gap-6">
              <p className="font-mono text-sm text-amber sm:col-span-2">{passo.n}</p>
              <div className="sm:col-span-10">
                <p className="text-fg">{passo.nome}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{passo.texto}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-line bg-surface p-5">
          <h3 className="font-display text-2xl text-fg">No Termux</h3>
          <pre className="mt-3 whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-fg">{BLOCO_TERMUX}</pre>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Cole o bloco inteiro de uma vez. O Termux aceita várias linhas juntas. Ele mesmo acha o arquivo na pasta Download do celular. Se aparecer Achei: nada, o download não caiu nessa pasta.
          </p>
        </article>
        <article className="rounded-2xl border border-line bg-surface p-5">
          <h3 className="font-display text-2xl text-fg">No computador</h3>
          <pre className="mt-3 whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-fg">{`adb connect 192.168.1.88:5555
python speedtvbox.py`}</pre>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Troque o IP pelo da TV Box. Rode na pasta onde estão o platform-tools e o arquivo baixado. Se o comando adb não existir, entre na pasta do platform-tools.
          </p>
        </article>
      </section>

      <section className="rounded-2xl border border-line bg-bg-raised p-5 sm:p-6">
        <h2 className="font-display text-3xl text-fg">O que a opção 1 faz</h2>
        <ol className="mt-4 space-y-3 text-sm leading-relaxed text-muted">
          <li>
            <span className="text-fg">Lê, sem desativar.</span> RAM verdadeira contra a da etiqueta, Android da tela Sobre contra o kernel, Widevine, pacotes, app escondido e nome de vírus.
          </li>
          <li>
            <span className="text-fg">Pergunta do risco.</span> Adups e o backdoor XCPE (com.oemservice) são desativados se você disser sim. Não são apagados: a firmware reporia o arquivo.
          </li>
          <li>
            <span className="text-fg">Pergunta do que veio de fábrica.</span> Netflix, Kodi, Prime, Disney, Globoplay. YouTube da TV fica. Play Store, GMS, WebView, launcher, teclado, HDMI e codec não entram.
          </li>
          <li>
            <span className="text-fg">Limpa em ondas.</span> Calendário, telefone, mapa, impressão e telemetria. Reinicia. Se a tela inicial, a loja ou o SystemUI quebrarem, desfaz a onda.
          </li>
          <li>
            <span className="text-fg">Relatório.</span> Abra o app Arquivos, pasta Download, pasta SpeedTV. Em português: aplicativos antes e depois, o que foi desligado, RAM de vitrine contra a real, Android de vitrine contra o kernel, Widevine.
          </li>
        </ol>
      </section>

      <section>
        <h2 className="font-display text-3xl text-fg">Não faça</h2>
        <ul className="mt-4 space-y-2 text-sm leading-relaxed text-muted">
          <li>Não comece pela limpeza solta nem pela Play Store. Na primeira vez a opção é a 1.</li>
          <li>Não confirme o recovery se a linha selecionada não estiver visível.</li>
          <li>Não apague pacote de sistema com outro programa. Aí o reset deixa de desfazer.</li>
          <li>Se a TV não voltar depois de uma onda, tire da tomada por 30 segundos. Se continuar morta, repita o reset de fábrica.</li>
        </ul>
      </section>
    </div>
  );
}

async function lerAgente(): Promise<string> {
  const res = await fetch(FILE);
  if (!res.ok) throw new Error("não carregou o agente");
  return res.text();
}

async function shaCurto(texto: string): Promise<string> {
  const data = new TextEncoder().encode(texto);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 16);
}

function personalizar(texto: string, ip: string, api: string): string {
  let alvo = ip.trim();
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(alvo)) alvo += ":5555";
  const partes = alvo.split(":");
  const octetos = partes[0].split(".");
  const porta = Number(partes[1]);
  const ipValido = octetos.length === 4 && octetos.every((parte) => /^\d{1,3}$/.test(parte) && Number(parte) >= 0 && Number(parte) <= 255);
  if (!ipValido || partes.length !== 2 || !Number.isInteger(porta) || porta < 1 || porta > 65535) {
    throw new Error("IP inválido. Use um IPv4 válido, com porta opcional (ex.: 192.168.1.88:5555).");
  }
  const chave = api.trim();
  if (!/^[A-Za-z0-9_-]{20,256}$/.test(chave)) {
    throw new Error("Cole a chave do Gemini, numa linha só.");
  }
  const comIp = texto.replace(/DISPOSITIVO_PADRAO = "[^"]*"/, `DISPOSITIVO_PADRAO = "${alvo}"`);
  const pronto = comIp.replace(/API_KEY_PADRAO = "[^"]*"/, `API_KEY_PADRAO = "${chave}"`);
  if (pronto === texto) throw new Error("Não achei onde gravar IP e chave neste arquivo.");
  return pronto;
}

function baixar(texto: string, nome: string) {
  const blob = new Blob([texto], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export function Console() {
  const [aviso, setAviso] = useState("");
  const [codigo, setCodigo] = useState("");
  const [aberto, setAberto] = useState(false);
  const [hash, setHash] = useState("");
  const [ip, setIp] = useState("192.168.1.88:5555");
  const [api, setApi] = useState("");
  const [lembrarChave, setLembrarChave] = useState(false);
  const [aba, setAba] = useState<"baixar" | "tutorial">("baixar");

  useEffect(() => {
    let vivo = true;
    const ipSalvo = localStorage.getItem("speedtv-ip") || localStorage.getItem("nexo-ip");
    const apiSalva = localStorage.getItem("speedtv-api") || localStorage.getItem("nexo-api");
    if (ipSalvo) setIp(ipSalvo);
    if (apiSalva) {
      setApi(apiSalva);
      setLembrarChave(true);
    }
    lerAgente()
      .then(async (texto) => {
        if (!vivo) return;
        setCodigo(texto);
        if (!ipSalvo) {
          const achado = texto.match(/DISPOSITIVO_PADRAO = "([^"]+)"/);
          if (achado) setIp(achado[1]);
        }
        if (!apiSalva) {
          const achado = texto.match(/API_KEY_PADRAO = "([^"]+)"/);
          if (achado) setApi(achado[1]);
        }
        setHash(await shaCurto(texto));
      })
      .catch(() => {
        if (vivo) setAviso("O arquivo do agente não carregou. Recarregue a página.");
      });
    return () => {
      vivo = false;
    };
  }, []);

  function comPersonalizado(fn: (texto: string) => void) {
    comTexto((bruto) => {
      try {
        const pronto = personalizar(bruto, ip, api);
        localStorage.setItem("speedtv-ip", ip.trim());
        if (lembrarChave) {
          localStorage.setItem("speedtv-api", api.trim());
        } else {
          localStorage.removeItem("speedtv-api");
          localStorage.removeItem("nexo-api");
        }
        fn(pronto);
      } catch (erro) {
        setAviso(erro instanceof Error ? erro.message : "Não deu para montar o arquivo.");
      }
    });
  }

  async function comTexto(fn: (texto: string) => void) {
    try {
      const texto = codigo || (await lerAgente());
      if (!codigo) setCodigo(texto);
      fn(texto);
    } catch {
      setAviso("Não consegui ler o agente.");
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 pb-24 pt-8 sm:px-6 sm:pt-12">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <p className="font-mono text-xs tracking-widest text-amber">CAMPO · TV BOX</p>
          <h1 className="font-display text-5xl leading-none text-fg sm:text-6xl">SpeedTV Box</h1>
        </div>
        <p className="max-w-xs text-sm text-muted">
          Versão 8. A memória disponível considera MemAvailable ou livre + cache nos kernels antigos. O relatório e a sessão ficam em Download/SpeedTV.
        </p>
      </header>

      <div className="mt-6 flex gap-2">
        <button
          type="button"
          aria-pressed={aba === "baixar"}
          className={`inline-flex min-h-11 items-center rounded-xl px-4 text-sm ${aba === "baixar" ? "bg-amber font-semibold text-amber-ink" : "border border-line text-fg"}`}
          onClick={() => setAba("baixar")}
        >
          Baixar
        </button>
        <button
          type="button"
          aria-pressed={aba === "tutorial"}
          className={`inline-flex min-h-11 items-center rounded-xl px-4 text-sm ${aba === "tutorial" ? "bg-amber font-semibold text-amber-ink" : "border border-line text-fg"}`}
          onClick={() => setAba("tutorial")}
        >
          Tutorial
        </button>
      </div>

      {aba === "tutorial" ? (
        <Tutorial />
      ) : (
        <>

      <section className="mt-8 grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-line bg-surface p-5 sm:p-6 lg:col-span-2">
          <p className="font-mono text-xs text-faint">sua TV Box, neste arquivo</p>
          <label className="mt-3 block text-sm text-muted" htmlFor="nexo-ip">
            IP da TV
            <input
              id="nexo-ip"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              suppressHydrationWarning
              className="mt-1 w-full rounded-xl border border-line bg-bg-raised px-3 py-3 font-mono text-base text-fg"
            />
          </label>
          <label className="mt-3 block text-sm text-muted" htmlFor="nexo-api">
            Chave do Gemini
            <input
              id="nexo-api"
              type="password"
              placeholder="cole a chave do Gemini"
              value={api}
              onChange={(e) => setApi(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              suppressHydrationWarning
              className="mt-1 w-full rounded-xl border border-line bg-bg-raised px-3 py-3 font-mono text-sm text-fg"
            />
          </label>
          <label className="mt-3 flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={lembrarChave} onChange={(e) => setLembrarChave(e.target.checked)} />
            Lembrar a chave neste navegador
          </label>
          <p className="mt-2 text-sm text-muted">
            O .py baixado já sai com IP e chave gravados. Se não marcar a opção acima, a chave não fica salva no navegador, mas continua dentro do arquivo que você baixar.
          </p>
          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-amber px-4 text-sm font-semibold text-amber-ink"
              onClick={() => comPersonalizado((t) => baixar(t, "speedtvbox.py"))}
            >
              <Download className="size-4" aria-hidden="true" />
              Baixar .py
            </button>
            <button
              type="button"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-bg-raised px-4 text-sm text-fg"
              onClick={() => comPersonalizado((t) => baixar(t, "speedtvbox.txt"))}
            >
              Baixar .txt
            </button>
            <button
              type="button"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-bg-raised px-4 text-sm text-fg"
              onClick={() =>
                comPersonalizado(async (t) => {
                  await navigator.clipboard.writeText(t);
                  setAviso("Código copiado, já com este IP e esta chave.");
                })
              }
            >
              <Copy className="size-4" aria-hidden="true" />
              Copiar
            </button>
          </div>
          {hash ? (
            <p className="mt-3 font-mono text-xs text-faint">sha256 {hash}…</p>
          ) : null}
          {aviso ? <p className="mt-3 text-sm text-fg">{aviso}</p> : null}
        </div>

        <aside className="rounded-2xl border border-line bg-bg-raised p-5">
          <p className="font-display text-2xl text-fg">No Termux</p>
          <p className="mt-3 text-sm text-muted">Baixe o .py. Cole isto inteiro, de uma vez:</p>
          <pre className="mt-3 whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-fg">{BLOCO_TERMUX}</pre>
          <button
            type="button"
            className="mt-3 inline-flex min-h-11 items-center rounded-xl border border-line px-4 text-sm text-fg"
            onClick={() => {
              navigator.clipboard.writeText(BLOCO_TERMUX).then(() => {
                setAviso("Comandos copiados. No Termux, segure a tela e cole tudo de uma vez.");
              });
            }}
          >
            Copiar comandos
          </button>
          <p className="mt-3 text-sm text-muted">Na primeira vez, escolha 1. O reset está na aba Tutorial.</p>
        </aside>
      </section>

      <section className="mt-10 grid gap-4 md:grid-cols-2">
        <article className="rounded-2xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2 text-amber">
            <Activity className="size-4" aria-hidden="true" />
            <p className="font-mono text-xs tracking-wide">MISSÃO 1</p>
          </div>
          <h2 className="mt-2 font-display text-4xl leading-none">Limpeza que mede</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Desativa para o usuário, reinicia, espera o boot e confere SystemUI, Ajustes, a mesma tela inicial e a Play Store ainda ligada. Se a onda não passar, ela é desfeita e as anteriores ficam. Nada é apagado de /system — o reset físico continua valendo.
          </p>
        </article>
        <article className="rounded-2xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2 text-amber">
            <Store className="size-4" aria-hidden="true" />
            <p className="font-mono text-xs tracking-wide">MISSÃO 2</p>
          </div>
          <h2 className="mt-2 font-display text-4xl leading-none">Loja que não abre</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Religa GMS, GSF, loja, downloads e WebView. Tira atualização quebrada, limpa cache, tenta abrir, lê o logcat e só então apaga os dados da loja. Dados do Play Services não são apagados — isso desloga a conta. O Gemini sugere; a lista branca executa.
          </p>
        </article>
      </section>

      <section className="mt-10">
        <h2 className="font-display text-3xl">O caminho da opção 1</h2>
        <ol className="mt-4 divide-y divide-line border-y border-line">
          {ONDAS.map((onda) => (
            <li key={onda.n} className="grid gap-2 py-4 sm:grid-cols-12 sm:gap-6">
              <p className="font-mono text-sm text-amber sm:col-span-2">{onda.n}</p>
              <div className="sm:col-span-10">
                <p className="text-fg">{onda.nome}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{onda.texto}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-10">
        <h2 className="font-display text-3xl">O que a auditoria olha</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {MEDIDAS.map(([nome, texto]) => (
            <article key={nome} className="rounded-xl border border-line bg-bg-raised p-4">
              <h3 className="font-display text-2xl text-fg">{nome}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{texto}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-10 grid gap-4 lg:grid-cols-2">
        <div>
          <h2 className="font-display text-3xl">Reparo da loja</h2>
          <ol className="mt-4 space-y-2 text-sm text-muted">
            <li>Abre uma vez e guarda o erro, antes de mudar qualquer coisa.</li>
            <li>Liga hora automática. Reativa, desesconde e reinstala o que foi tirado só do usuário.</li>
            <li>Confere o provedor de WebView. Atualização incompatível volta para a de fábrica.</li>
            <li>Limpa cache da loja e do GMS. Não limpa dados do GMS.</li>
            <li>Se ainda cair, desatualiza a própria loja, limpa os dados dela e reinicia.</li>
            <li>O que sobrar vai para o Gemini 3.8, com ação recusada se sair da lista.</li>
          </ol>
        </div>
        <div className="rounded-2xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2 text-amber">
            <Shield className="size-4" aria-hidden="true" />
            <p className="font-mono text-xs tracking-wide">PORTÃO</p>
          </div>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>Não existe `pm uninstall` de sistema neste agente.</li>
            <li>App que você instalou não entra na onda. Spyware de nome conhecido pede confirmação.</li>
            <li>Launcher atual, teclado atual e entrada HDMI são protegidos na hora, não só por lista.</li>
            <li>Widevine: nunca apaga a biblioteca. Esconde com root e o reverter devolve.</li>
            <li>Os relatórios vão para Download/SpeedTV, a pasta que abre no app Arquivos.</li>
            <li>Se a TV Box não voltar no ADB: tire da tomada 30 segundos. O reset físico desfaz o resto.</li>
          </ul>
        </div>
      </section>

      <section className="mt-10">
        <div className="flex items-center gap-2">
          <Radio className="size-4 text-amber" aria-hidden="true" />
          <h2 className="font-display text-3xl">Comandos</h2>
        </div>
        <div className="mt-4 overflow-hidden rounded-xl border border-line">
          {COMANDOS.map(([cmd, nota]) => (
            <div
              key={cmd}
              className="grid gap-1 border-b border-line px-4 py-3 last:border-b-0 sm:grid-cols-3 sm:items-center"
            >
              <code className="font-mono text-xs text-fg sm:col-span-2 sm:text-sm">{cmd}</code>
              <span className="text-sm text-muted">{nota}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 flex items-start gap-2 text-sm text-muted">
          <RotateCcw className="mt-0.5 size-4 shrink-0 text-faint" aria-hidden="true" />
          Cole o bloco do Termux inteiro. Não use /sdcard: no Termux essa pasta não existe. O bloco procura o arquivo em Download sozinho.
        </p>
      </section>

      <section className="mt-10">
        <button
          type="button"
          className="inline-flex min-h-11 items-center rounded-xl border border-line px-4 text-sm text-fg"
          onClick={() => setAberto((v) => !v)}
        >
          {aberto ? "Esconder o código" : "Ver o código aqui"}
        </button>
        {aberto ? (
          <pre className="mt-4 max-h-96 overflow-auto rounded-xl border border-line bg-bg-raised p-4 font-mono text-xs leading-relaxed text-muted">
            {codigo || "carregando…"}
          </pre>
        ) : null}
        <p className="mt-4 text-xs leading-relaxed text-faint">
          A chave nunca é gravada no repositório. Ela entra no arquivo que você baixa; marque “Lembrar a chave” apenas se quiser mantê-la no armazenamento local deste navegador. Não publique o .py personalizado.
        </p>
      </section>
        </>
      )}
    </main>
  );
}
