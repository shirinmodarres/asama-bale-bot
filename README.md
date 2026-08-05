# asama-bot

Simple Python Bale bot MVP for the Atka sales goods request and seller product order flows.

Static data is manually maintained in one file, and runtime data is stored in MongoDB.

## Structure

- `bot/main.py` - application setup and handler registration.
- `bot/config.py` - environment config.
- `bot/handlers/` - start, seller, expert, manager, and admin command/callback handlers.
- `bot/services/` - user/request/order Mongo storage, Excel export, and notifications.
- `bot/utils/` - keyboards and helpers.
- `data/static_data.py` - single source of truth for stores, categories, products, experts, manager, and admin.
- `sefareshbot.py` - run wrapper.

## Static Data

Edit `data/static_data.py` before running:

- `SYSTEM_MANAGER`
- `SALES_MANAGER`
- `SALES_EXPERTS`
- `STORES`
- `CATEGORIES`

Each product has a `price` in rials. Set the real value before accepting
orders; approving each order unit credits 4% of its snapshotted product price
to the seller wallet.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Set your real bot token in `.env`:

```bash
APP_ENV=local
BOT_TOKEN_LOCAL=your-local-token
MONGO_URI_LOCAL=mongodb://localhost:27017
MONGO_DB_NAME_LOCAL=asama_bot_local

BOT_TOKEN_PRODUCTION=your-production-token
MONGO_URI_PRODUCTION=mongodb://localhost:27017
MONGO_DB_NAME_PRODUCTION=asama_bot
```

MongoDB must be running before starting the bot.

Use `APP_ENV=local` for local testing and `APP_ENV=production` only on the
production server. Local admins/manager/expert IDs can be set with
`LOCAL_ADMIN_IDS`, `LOCAL_SALES_MANAGER_ID`, and `LOCAL_EXPERT_ID`.

## Run

```bash
.venv/bin/python -m bot.main
```

or:

```bash
.venv/bin/python sefareshbot.py
```

## Commands

- `/start` - seller registration and seller menu.
- `/export_requests` - Excel export. Sales manager/admin export all requests; experts export assigned stores only.
- `/export_orders` - Excel export for product orders. Sales manager/admin only.
- `/info` - basic bot info for admin.

## Product Orders

Approved sellers create product orders from `ثبت سفارش کالا`.
The seller store is taken from `data/users.json`; sellers cannot choose another store.
Quantity means individual product units. For each unit, the bot collects one serial and one tracking code as text or photo.
Orders are saved with `pending_expert_validation` and sent to the assigned expert.
Experts can only validate orders for their assigned stores.
