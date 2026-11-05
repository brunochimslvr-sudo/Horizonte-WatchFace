# WatchFaces

Monorepo (privado) das watch faces Wear OS (Watch Face Format v4) para publicar e vender.

## Faces

| Face | Pasta | Status |
|------|-------|--------|
| Horizonte | `faces/horizonte` | em desenvolvimento |

## Estrutura

```
faces/<face>/        gen.py, src/ (gerado), prototipo/, store/ (textos e imagens da Play Store), version
shared/build.sh      build + assinatura de qualquer face
shared/tools/        Validate.java e schema WFF v4
dist/                APKs finais (ignorado pelo git)
docs/                notas de publicação
```

## Build

```bash
bash shared/build.sh <face>          # gera dist/<face>.apk
bash shared/build.sh <face> --bump   # incrementa o versionCode antes
```

## Nova face

1. Copie `faces/horizonte` para `faces/<nova>` e ajuste `gen.py` (applicationId próprio por face).
2. Rode `bash shared/build.sh <nova>`.

## Convenções

- Commits: `<face>: mensagem` ou `shared: mensagem`.
- Branches: `feat/<face>-<assunto>`.
- Tags de release: `<face>-v1.2.0`.
- Chave de publicação: fica FORA do repositório, com backup. `*.keystore` é ignorado.
