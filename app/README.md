# App de monitoramento (Android)

App Flutter do piloto. Dados fictícios. Login por e-mail e senha, a mesma API do painel web.

## Como o APK é gerado
O workflow `.github/workflows/app-android.yml` cria o projeto Android padrão e copia
`lib/` e `pubspec.yaml` daqui. O APK de teste (debug) fica como artefato do workflow.

## Instalar no celular (teste)
1. Baixe `monitor-iot-app-debug` no GitHub Actions e extraia o `app-debug.apk`.
2. Autorize a instalação de fontes desconhecidas no celular e instale o APK.

## Antes de uma versão para usuários
- Trocar o APK de debug por um APK assinado (release).
- Declarar a permissão de internet no manifesto de release.
