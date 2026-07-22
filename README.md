# asama-bot

Simple Python Telegram bot MVP for the Atka sales goods request and seller product order flows.

No backend or database is used. Static data is manually maintained in one file, and runtime data is stored in JSON files.

## Structure

- `bot/main.py` - application setup and handler registration.
- `bot/config.py` - environment config.
- `bot/handlers/` - start, seller, expert, manager, and admin command/callback handlers.
- `bot/services/` - user JSON storage, request/order JSON storage, Excel export, and notifications.
- `bot/utils/` - keyboards and safe JSON helpers.
- `data/static_data.py` - single source of truth for stores, categories, products, experts, manager, and admin.
- `data/users.json` - created automatically for runtime users/sellers.
- `data/requests.json` - created automatically for goods requests.
- `data/orders.json` - created automatically for seller product orders.
- `sefareshbot.py` - run wrapper.

## Static Data

Edit `data/static_data.py` before running:

- `SYSTEM_MANAGER`
- `SALES_MANAGER`
- `SALES_EXPERTS`
- `STORES`
- `CATEGORIES`

Each product has a `price` in tomans. Set the real value before accepting
orders; approving each order unit credits 2% of its snapshotted product price
to the seller wallet.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Set your real bot token in `.env`:

```bash
BOT_TOKEN=your-token
USERS_FILE=data/users.json
REQUESTS_FILE=data/requests.json
ORDERS_FILE=data/orders.json
```

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
