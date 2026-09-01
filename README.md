# Docker File Manager

MVP desktop para Linux que navega lado a lado pelo host e pelo filesystem de containers Docker locais. Permite upload e download de arquivos ou diretórios, seleção múltipla e drag-and-drop sem bloquear a interface.

## Decisões técnicas

As APIs de archive do Docker são suficientes para transferir dados, mas não constituem uma API completa de filesystem:

- `get_archive(path)` entrega um TAR em streaming e é usado em todo download.
- `put_archive(path, data)` recebe um TAR e é usado em todo upload.
- A Engine API não oferece operações próprias de listagem, rename, mkdir ou delete dentro do container.
- Para listar sem baixar recursivamente um diretório inteiro, o MVP executa `find` de modo somente leitura pelo endpoint Exec. Isso exige que a imagem tenha um `find` compatível com `-printf` (GNU findutils). Uma versão futura pode adicionar adaptadores para BusyBox e imagens minimalistas.
- Rename, mkdir e delete foram conscientemente deixados fora do MVP: exigiriam Exec mutável dentro do container (ou construções TAR limitadas), confirmação e uma política de segurança própria.

A UI só conversa com `ContainerFileSystem`, `DockerService` e `TransferService`; detalhes de Docker e TAR não ficam nos widgets. Transferências rodam em `QThreadPool`. Archives recebidos são copiados para arquivo temporário com spill para disco e extraídos manualmente. A extração rejeita path traversal, symlinks, hardlinks e arquivos especiais, além de nunca sobrescrever um destino existente.

Limitação do cancelamento: downloads são interrompidos entre chunks. Durante a chamada síncrona `put_archive`, o Docker SDK não fornece cancelamento cooperativo; o pedido passa a valer assim que essa chamada retorna.

## Instalação

Requisitos: Ubuntu/Linux, Python 3.10+ e Docker Engine local acessível pelo usuário.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
docker-file-manager
```

Alternativamente:

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m docker_file_manager.main
```

Se houver erro de acesso ao `/var/run/docker.sock`, ajuste a instalação do Docker ou a associação do usuário ao grupo `docker`; não execute a aplicação como root apenas para contornar permissões.

## Uso

Escolha um container no seletor. Duplo clique entra em diretórios; os botões permitem voltar, subir e atualizar. Arraste itens selecionados entre os painéis ou use **Enviar →** e **← Baixar**. Soltar sobre um diretório copia para ele; soltar no espaço vazio usa o caminho atual.

Arquivos existentes não são substituídos automaticamente. Links e arquivos especiais são recusados nas transferências do MVP.

## Testes

```bash
pip install -e '.[dev]'
pytest
```

Os testes unitários não exigem Docker e cobrem parsing da listagem e segurança da extração TAR. O log fica em `~/.local/share/docker-file-manager/logs/application.log` e nunca registra conteúdo de arquivos.

## Organização

```text
src/docker_file_manager/
├── main.py
├── models/
├── services/
├── ui/
└── workers/
```
