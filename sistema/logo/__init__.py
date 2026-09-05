"""Gerador de Logo 3D, montado dentro do sistema em /logo.

Os arquivos aqui sao os do morumbi3d_web, praticamente como estavam. As
unicas mudancas: as chamadas de API da interface passaram a derivar do
caminho atual (para funcionar montadas sob /logo E sozinhas na raiz), e a
autenticacao Basic saiu, porque quem guarda a porta agora e a sessao do
sistema — ver wsgi.py.
"""
