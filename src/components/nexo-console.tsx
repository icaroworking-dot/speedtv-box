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
    nome: "Diagnóstico",
    texto:
      "Uma leitura só: RAM real contra a de vitrine, SDK contra o kernel, Widevine, biblioteca OEM, armazenamento, ZRAM, Play Store, porta aberta e o backdoor XCPE (com.oemservice).",
  },
  {
    n: "02",
    nome: "Limpar",
    texto:
      "Ondas de disable-user com reboot e checagem. Não mexe em launcher, loja, GMS, WebView, teclado, HDMI nem SystemUI. YouTube, Netflix, Prime e Disney ficam.",
  },
  {
    n: "03",
    nome: "Loja e segurança",
    texto:
      "O reparo da Play Store que já funcionou na sua caixa continua. A opção Segurança desativa Adups e o XCPE sem apagar o APK — a firmware reporia o arquivo.",
  },
  {
    n: "04",
    nome: "Widevine",
    texto:
      "Não fabrica L1. Se o L1 da caixa for falso e o app ficar em tela preta, com root esconde liboemcrypto.so. O Android assume L3 de verdade e o vídeo protegido toca em SD. Reverter devolve o arquivo.",
  },
  {
    n: "05",
    nome: "Afinar",
    texto:
      "Cache, DNS, Wi-Fi sem dormir, caixa ligada enquanto estiver na tomada, ZRAM só com root, 1080p só se a RAM real for baixa.",
  },
];

const MEDIDAS = [
  ["RAM", "meminfo, mapa iomem e dumpsys. Se a prop disser 4 GB e o kernel mostrar menos, o relatório marca vitrine."],
  ["Android", "SDK, release e kernel. Android 14 em kernel 4.4 é mentira de firmware, não é patch velho."],
  ["Widevine", "Lê o nível e a biblioteca OEM. L1 de caixa genérica é vitrine até um app protegido tocar. Não existe atalho para 4K."],
  ["Ameaça", "Adups, OTA silenciosa e o backdoor XCPE (com.oemservice / x.cpe), que aluga o IP da casa e volta da partição /oem."],
  ["Play", "O que está desativado, escondido ou removido só para o usuário, inclusive WebView e Trichrome."],
  ["Termux", "O relatório vai para a pasta SpeedTV, na memória interna, ao lado de Download."],
];

const COMANDOS = [
  ["python speedtvbox.py", "menu curto"],
  ["python speedtvbox.py diagnostico", "só leitura"],
  ["python speedtvbox.py debloat", "ondas, com pergunta"],
  ["python speedtvbox.py playstore", "reparo da loja"],
  ["python speedtvbox.py seguranca", "XCPE e Adups"],
  ["python speedtvbox.py widevine", "L3 de verdade, se quiser"],
  ["python speedtvbox.py afinar", "cache, rede, 1080p"],
  ["python speedtvbox.py reverter", "desfaz o que o SpeedTV Box mudou"],
];

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
  if (!/^(\d{1,3}\.){3}\d{1,3}:\d{2,5}$/.test(alvo)) {
    throw new Error("IP inválido. Use 192.168.1.88 ou 192.168.1.88:5555");
  }
  const chave = api.trim();
  if (chave.length < 10 || /[\r\n"']/.test(chave)) {
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
  URL.revokeObjectURL(url);
}

export function Console() {
  const [aviso, setAviso] = useState("");
  const [codigo, setCodigo] = useState("");
  const [aberto, setAberto] = useState(false);
  const [hash, setHash] = useState("");
  const [ip, setIp] = useState("192.168.1.88:5555");
  const [api, setApi] = useState("");

  useEffect(() => {
    let vivo = true;
    const ipSalvo = localStorage.getItem("speedtv-ip") || localStorage.getItem("nexo-ip");
    const apiSalva = localStorage.getItem("speedtv-api") || localStorage.getItem("nexo-api");
    if (ipSalvo) setIp(ipSalvo);
    if (apiSalva) setApi(apiSalva);
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
        localStorage.setItem("speedtv-api", api.trim());
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
          Versão 4. Cada exame explica o que achou e pergunta antes de mexer.
        </p>
      </header>

      <section className="mt-8 grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-line bg-surface p-5 sm:p-6 lg:col-span-2">
          <p className="font-mono text-xs text-faint">sua caixa, neste arquivo</p>
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
              placeholder="cole a chave do Gemini"
              value={api}
              onChange={(e) => setApi(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              suppressHydrationWarning
              className="mt-1 w-full rounded-xl border border-line bg-bg-raised px-3 py-3 font-mono text-sm text-fg"
            />
          </label>
          <p className="mt-2 text-sm text-muted">
            O download já sai com esses dois gravados. No Termux não precisa colar nada.
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
          <ol className="mt-3 space-y-3 text-sm text-muted">
            <li>
              <span className="text-fg">1.</span> Baixe o .py. O celular e a caixa no mesmo Wi-Fi.
            </li>
            <li>
              <span className="font-mono text-xs text-fg">cp /sdcard/Download/speedtvbox.py $HOME/</span>
            </li>
            <li>
              <span className="font-mono text-xs text-fg">cd $HOME</span>
            </li>
            <li>
              <span className="font-mono text-xs text-fg">python speedtvbox.py</span>
            </li>
            <li>
              <span className="text-fg">2.</span> Na TV, aceite a depuração. Android 11+ pede o código de pareamento; o menu pergunta.
            </li>
          </ol>
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
        <h2 className="font-display text-3xl">O que mudou</h2>
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
            <li>O journal e os logs vão para a pasta SpeedTV, na memória interna, ao lado de Download.</li>
            <li>Caixa que não volta no ADB: tire da tomada 30 segundos. O reset físico desfaz o resto.</li>
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
          No Termux use <span className="font-mono text-fg">$HOME</span>, nunca um til com barra. Se o arquivo baixado estiver na raiz da memória, e não dentro de Download, tire o <span className="font-mono text-fg">Download/</span> do comando. A Aquaris e a MXQ entram pelo mesmo fluxo.
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
          A página não guarda a chave. Ela entra só no arquivo que você baixa, no seu celular. Não suba esse arquivo baixado num GitHub público.
        </p>
      </section>
    </main>
  );
}
