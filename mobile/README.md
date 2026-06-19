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
