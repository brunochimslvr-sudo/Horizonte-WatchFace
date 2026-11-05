# Instalar o Horizonte no Galaxy Watch 8

O APK pronto está em `dist/horizonte.apk`. Para gerar de novo depois de mudar algo no `gen.py`:

```bash
bash shared/build.sh horizonte
```

## 1. Ativar a depuração no relógio (uma vez)

1. No relógio: **Configurações → Sobre o relógio → Software** e toque 5 vezes em **Versão do software** até aparecer "Modo desenvolvedor ativado".
2. Volte para **Configurações → Opções do desenvolvedor**.
3. Ligue **Depuração ADB** e **Depuração por Wi-Fi**.
4. O relógio e o PC precisam estar na **mesma rede Wi-Fi**.

## 2. Conectar o PC ao relógio

Em **Depuração por Wi-Fi**, toque em **Parear novo dispositivo**. O relógio mostra um IP:porta e um código de 6 dígitos. No terminal do PC:

```bash
"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" pair IP:PORTA_DO_PAREAMENTO
```

Digite o código quando pedir. Depois use o IP:porta que aparece na tela principal de Depuração por Wi-Fi (a porta é outra):

```bash
"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" connect IP:PORTA
```

## 3. Instalar

```bash
"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" install -r dist/horizonte.apk
```

## 4. Escolher a watch face

No relógio, mantenha o dedo na tela inicial, deslize até o fim, toque em **+** (adicionar) e escolha **Horizonte**. Para trocar as informações dos cantos, mantenha o dedo na watch face e toque em **Personalizar**.

## Se algo não aparecer

Veja o log do relógio enquanto escolhe a face:

```bash
adb logcat --pid=$(adb shell pidof -s com.google.wear.watchface.runtime)
```

Mande o erro que aparecer que eu ajusto o `gen.py`.

## Pontos ainda não testados em relógio de verdade

- Cores do céu mudando com a hora (usam `extractColorFromColors` com 25 cores por faixa).
- Texto curvo nos cantos (`TextCircular`).
- Barra de bateria no horizonte (`BATTERY_PERCENT`, cor por nível e raio ao carregar com `BATTERY_CHARGING_STATUS`) e largura da barra via `Transform` no `Rectangle`.
- Complicações padrão do topo e da base (passos, batimentos, notificações, próximo evento).
- Nascer e pôr do sol do arco estão fixos em 05:30 e 18:15 (`SUNRISE` e `SUNSET` no `gen.py`), porque o formato não tem essa fonte de dados.
