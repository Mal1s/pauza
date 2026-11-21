# ПАУЗА — Telegram-бот набора игроков

Long-polling Telegram-бот для анкет футболистов команды «ПАУЗА» и работы тренеров с заявками в закрытой группе. Продукт работает только в Telegram; сайт и Mini App не нужны.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `python3.11 -m pauza_bot.main` — run the PAUZA Telegram bot
- `python3.11 -m unittest discover -s tests -v` — test bot validation and database logic
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env for the API server: `DATABASE_URL` — Postgres connection string
- Required Replit Secrets for the Telegram bot: `BOT_TOKEN`, `ADMIN_CHAT_ID`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)
- Telegram bot: Python 3.11, aiogram 3, aiosqlite and SQLite

## Where things live

- `pauza_bot/main.py` — bot handlers, player questionnaire, admin actions and commands
- `pauza_bot/keyboards.py` — inline keyboard layouts
- `pauza_bot/texts.py` — editable bot copy, labels and emojis
- `pauza_bot/db.py` — SQLite schema and queries
- `pauza_bot/README.md` — bot setup and long-running deployment notes
- `tests/test_bot_core.py` — bot validation and persistence tests

## Architecture decisions

- The applicant flow edits one Telegram message; FSM drafts live in memory and are lost on restart.
- Submitted applications and coach notes persist in the SQLite database.
- The bot runs by long polling and must use a long-lived worker process for 24/7 operation.

## Product

- Player applications (including optional additional information), coach review cards, accept/reject actions, trial notifications, notes, search, statistics and CSV export.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
