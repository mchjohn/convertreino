# ConverTreino Mobile

App Expo (SDK 56) com OAuth Strava, sessão JWT e chat conversacional.

## Requisitos

- Node.js 20+
- Backend ConverTreino em execução (SPEC-013 / SPEC-014)
- Conta de desenvolvedor Strava

## Setup

```bash
cd mobile
npm install
cp .env.example .env
```

### Variáveis de ambiente (`EXPO_PUBLIC_*`)

| Variável | Obrigatória | Exemplo dev | Descrição |
|----------|-------------|-------------|-----------|
| `EXPO_PUBLIC_API_BASE_URL` | Sim | `http://localhost:8000` | Base URL da API FastAPI |
| `EXPO_PUBLIC_STRAVA_CLIENT_ID` | Sim | ID do painel Strava | Client ID público |
| `EXPO_PUBLIC_STRAVA_REDIRECT_URI` | Sim | `convertreino://oauth/callback` | Deep link OAuth |

No emulador Android, use `http://10.0.2.2:8000` como `EXPO_PUBLIC_API_BASE_URL` para alcançar o host.

### Dispositivo físico com ngrok

Em um celular real, `localhost` aponta para o próprio aparelho — a API no seu computador não é acessível. Use [ngrok](https://ngrok.com/download) para expor o backend local:

1. Inicie o backend na porta 8000 (veja [`backend/README.md`](../backend/README.md)).
2. Em outro terminal, crie o túnel:

```bash
ngrok http 8000
```

3. Copie a URL HTTPS exibida (ex.: `https://abcd-1234.ngrok-free.app`).
4. Atualize `mobile/.env`:

```bash
EXPO_PUBLIC_API_BASE_URL=https://abcd-1234.ngrok-free.app
```

5. Reinicie o Expo com cache limpo para recarregar as variáveis:

```bash
npx expo start -c
```

No plano gratuito, a URL do ngrok muda a cada execução — atualize o `.env` e reinicie o Expo sempre que reiniciar o túnel.

### Strava — Authorization Callback

1. Acesse [developers.strava.com](https://developers.strava.com) → **My API Application**.
2. Em **Authorization Callback Domain**, registre o host do redirect mobile (para `convertreino://oauth/callback`, use o domínio configurado no painel ou o URI completo conforme a documentação Strava).
3. Adicione `convertreino://oauth/callback` como redirect autorizado.
4. No backend, configure `STRAVA_MOBILE_REDIRECT_URI=convertreino://oauth/callback` quando diferente de `STRAVA_REDIRECT_URI`.

## Executar

```bash
npx expo start
```

Fluxo: Login Strava → sync automático de atividades → chat com GiftedChat.

## Testes

```bash
npm test
npm run test:coverage
```

Cobertura mínima de 70% em `src/services/*` e `src/lib/chatMappers.ts`.

## Deep link

- Scheme: `convertreino`
- Callback OAuth: `convertreino://oauth/callback`
