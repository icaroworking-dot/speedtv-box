# SpeedTV Box

Página que monta o agente de TV Box. A pessoa cola o IP da caixa e a chave do Gemini; o arquivo `speedtvbox.py` que desce já vai com os dois. O repositório não guarda chave.

No celular, no Termux:

```bash
termux-setup-storage
cp /sdcard/Download/speedtvbox.py $HOME/
cd $HOME
python speedtvbox.py
```

Os relatórios ficam na pasta `SpeedTV`, na memória interna, ao lado de Download.

## Atualizar

- Pedir a atualização aqui e ela sobe neste repositório.
- Ou editar o arquivo no site do GitHub e confirmar o commit.
- Quem já baixou o `.py` precisa baixar de novo. O celular não se atualiza sozinho.

O GitHub guarda o código. Para a página ficar no ar com atualização automática a cada envio, importe este repositório na Vercel. O botão Publicar desta conversa também coloca a página no ar.
