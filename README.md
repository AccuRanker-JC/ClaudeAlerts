# AccuRanker preferred URL-overvågning

Sender en mail via Resend, hvis et søgeord på PengeSparet.dk (domain_id 343517)
stopper med at matche sin "preferred landing page" i AccuRanker.

Kører automatisk hver dag kl. 06:00 UTC via GitHub Actions. Alarmen trigges kun
ved selve overgangen fra "matcher" til "matcher ikke længere" — ikke for
søgeord der allerede ikke matchede i går.

## Sådan sætter du det op

### 1. Opret et GitHub-repo
Opret et nyt (gerne privat) repo, og upload disse tre filer i denne struktur:

```
.
├── check_preferred_url.py
├── .github/
│   └── workflows/
│       └── preferred-url-check.yml
└── state.json   ← opret en tom fil med indholdet: {}
```

`state.json` skal eksistere fra start (bare med indholdet `{}`), så scriptet kan
gemme sin første baseline.

### 2. Opret en Resend-konto
1. Gå til resend.com og opret en konto **med jakob@accuranker.com** som login-mail
   (det er vigtigt — uden domæneverificering kan Resend kun sende til den mail,
   kontoen er oprettet med).
2. Under "API Keys" → opret en ny nøgle (Sending access er nok).
3. Gem nøglen — den vises kun én gang.

### 3. Generér en ny AccuRanker API-nøgle
Da den forrige nøgle blev delt i en chat, anbefaler jeg at oprette en ny under
AccuRanker → Kontoindstillinger → API, og bruge den nye her.

### 4. Tilføj GitHub Secrets
I dit repo: **Settings → Secrets and variables → Actions → New repository secret**.
Opret disse fire:

| Secret navn | Værdi |
|---|---|
| `ACCURANKER_API_KEY` | Din (nye) AccuRanker API-nøgle |
| `RESEND_API_KEY` | Din Resend API-nøgle |
| `ALERT_EMAIL_TO` | jakob@accuranker.com |
| `ALERT_EMAIL_FROM` | onboarding@resend.dev |

### 5. Test det manuelt
Gå til fanen **Actions** i dit repo → vælg workflowet "AccuRanker preferred URL
check" → klik **Run workflow** for at teste det med det samme, uden at vente på
kl. 06:00.

Første gang det kører, gemmes bare en baseline (ingen mail sendes). Anden gang
(og fremover) sender det kun mail, hvis noget er ændret sig til at IKKE matche
længere.

### 6. Løbende
Herefter kører det automatisk hver dag. Du kan altid trigge en manuel kørsel
via "Run workflow", hvis du vil teste en ændring.

## Justeringer du nemt selv kan lave
- **Tidspunkt**: ret `cron: "0 6 * * *"` i workflow-filen (tid er i UTC).
- **Andet domæne**: ret `ACCURANKER_DOMAIN_ID` i workflow-filen.
- **Flere modtagere**: ret `ALERT_EMAIL_TO`-secret'en (kommasepareret understøttes
  ikke direkte i scriptet lige nu — sig til, hvis du vil have flere modtagere,
  så tilføjer jeg det).
