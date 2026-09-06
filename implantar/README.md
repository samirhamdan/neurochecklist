# Sincronizar: aqui → git → VPS

O modelo é **git como fonte da verdade**. Ninguém edita arquivo direto no
servidor; o servidor puxa do repositório. Isso não é preciosismo: hoje a
atualização é `scp` de um zip e `cp -r` por cima, e não há como saber depois
qual versão está no ar nem como voltar quando quebra.

```
  seu computador  ──push──>  GitHub  <──pull──  VPS
                                               /opt/morumbi3d
```

## O que NUNCA vem do git

`/etc/systemd/system/morumbi3d.service`. O arquivo que está rodando tem três
coisas que o repositório não sabe:

| | no repositório (modelo) | no VPS (real) |
| --- | --- | --- |
| `MORUMBI_SENHA` | `TROQUE_ESTA_SENHA` | a senha de verdade |
| `MORUMBI_BIND` | `172.18.0.1:5000` | idem — mas confira |
| `MORUMBI_WORKERS` / `MemoryMax` | 1 / 800M | confira os desta máquina |

Sobrescrever esse arquivo a partir do git faz duas estragos de uma vez: o
site sai do ar (o Caddy roda em container e não alcança o `127.0.0.1` do
host) e a autenticação desliga (sem `MORUMBI_SENHA` o app fica aberto). Por
isso `atualizar.sh` não encosta nele — e lê o `MORUMBI_BIND` de dentro do
systemd para saber onde conferir se o serviço subiu.

## Primeira vez: `instalar.sh`

A instalação de hoje é uma pasta solta com o gerador de logo. `instalar.sh`
a troca pelo repositório, **mantendo o que não pode ser refeito**:

```bash
# no VPS, como root
bash /caminho/instalar.sh git@github-morumbi3d:samirhamdan/morumbi3d.git
```

| Preservado | Por quê |
| --- | --- |
| `venv/` | 180 MB já instalados. Refazer num VPS de 2 GB demora e às vezes falha por falta de RAM |
| `/var/lib/morumbi3d` | os uploads e o banco. O script não encosta |
| `morumbi3d.service` | a senha real, o bind do Docker e os limites desta máquina |

Do serviço ele muda **uma linha só**: `MORUMBI_WORKERS` para 1, porque o
processo agora carrega painel e gerador juntos. O `ExecStart` continua igual
— `wsgi.py` e `gunicorn.conf.py` ficaram na raiz, que já é o
`WorkingDirectory`.

**Se o serviço não voltar em 40 segundos, ele desfaz tudo sozinho**: devolve
os arquivos antigos do backup, devolve o arquivo do serviço e reinicia. O
comando para desfazer à mão também é impresso no fim, com os caminhos já
preenchidos.

Havia aqui um `migrar-para-git.sh` que comparava arquivo a arquivo e parava
se o servidor estivesse na frente. Ele foi **removido**: aquela comparação
supunha que a pasta do VPS fosse cópia exata de uma subpasta do repositório,
e depois da junção não é mais — parte dos arquivos do servidor foi
substituída por equivalentes na raiz. Rodá-lo hoje daria uma recusa que
parece erro e não é. A pergunta que ele existia para responder — *o servidor
tem algo que o repositório não tem?* — foi respondida comparando os arquivos
na mão: `gerar_logo_3d.py` idêntico, `app.py` e `index.html` diferindo só
pelas alterações da junção, e os sete arquivos que só existiam no VPS estão
agora em [`sistema/logo/anterior/`](../sistema/logo/anterior/) e no
`CLAUDE.md` da raiz.

## Repositório privado: chave de deploy

O VPS precisa se autenticar. Chave de deploy é melhor que token pessoal —
serve só para esse repositório e é revogável sozinha.

```bash
# no VPS
ssh-keygen -t ed25519 -f /root/.ssh/morumbi3d_deploy -N "" -C "vps-morumbi3d"
cat /root/.ssh/morumbi3d_deploy.pub
```

Cole a saída em **Settings → Deploy keys → Add deploy key** do repositório,
sem marcar "Allow write access" (o servidor só lê). Depois:

```bash
cat >> /root/.ssh/config <<'EOF'
Host github-morumbi3d
  HostName github.com
  User git
  IdentityFile /root/.ssh/morumbi3d_deploy
  IdentitiesOnly yes
EOF
# e use esta URL no clone:
#   git@github-morumbi3d:samirhamdan/morumbi3d.git
```

## Dia a dia

```bash
# no seu computador
git add -A && git commit -m "o que mudou" && git push

# no VPS
/opt/morumbi3d/implantar/atualizar.sh
```

`atualizar.sh` mostra o que vai entrar, atualiza o venv **só quando o
`requirements.txt` da raiz mudou** (esta máquina não tem RAM sobrando para um
`pip install` a cada deploy), reinicia, e **confere se o serviço voltou**.
Se não voltar em 30 segundos, ele desfaz sozinho e deixa a versão anterior
no ar. A conferência bate em `/saude`, que responde sem senha — a raiz
redirecionaria para a tela de entrada e um 302 não prova que o app está são. Deploy quebrado que fica quebrado até alguém reclamar é o que este
laço existe para evitar.

Alteração feita na unha dentro de `/opt/morumbi3d` é salva em
`/tmp/morumbi3d-local-*.patch` antes de ser descartada.

## Voltar uma versão à mão

```bash
cd /opt/morumbi3d
git log --oneline -10
git reset --hard <commit>
systemctl restart morumbi3d
```

O `venv/` e `/var/lib/morumbi3d` (os uploads) ficam fora do git e não são
tocados por nada disso.

## O que ainda não testei

Estes scripts foram exercitados contra um VPS **simulado** — repositório,
`systemctl` e `curl` de mentira — cobrindo: deploy sem novidade, deploy bom
com dependência nova, deploy quebrado (rollback automático confirmado),
alteração local preservada em patch, migração recusando quando o servidor
está na frente, e migração conectando quando bate. Nada disso rodou contra
a máquina de verdade, que eu não alcanço daqui. Rode a migração com o
backup à mão e confira `systemctl status morumbi3d` antes de sair.
