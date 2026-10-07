# Professional General Store POS

A production-ready General Store Point of Sale system built for PostgreSQL and Railway.

## Core Features

- Professional dark/black POS interface
- Shop name and logo management
- Barcode and QR scanning
- Multiple barcodes per product
- EAN-13, EAN-8, UPC-A, UPC-E, Code 128, Code 39, ITF, ITF-14, GS1-128, QR and custom/internal codes
- Leading-zero barcode preservation
- Product management
- Inventory management
- Stock adjustments and movement history
- Purchases and suppliers
- Customers and customer credit/udhaar
- Sales and complete sales history
- Item and bill discounts
- Fixed and percentage discounts
- Cash, card, bank transfer and other payments
- Split payments
- Cash received and change calculation
- Held/parked sales
- Sales returns and refunds
- Expenses
- Cash register/opening and closing
- Daily cash reconciliation
- Sales and profit reports
- Inventory reports
- Customer and supplier statements
- User accounts and roles
- Owner, Manager and Cashier roles
- Permission control
- Audit logging
- Receipt printing
- 58mm and 80mm thermal receipt support
- Receipt reprinting
- Configurable shop information
- Railway PostgreSQL deployment

## Important

This application intentionally does NOT contain a tax system.

There are no:
- Tax rates
- Tax calculations
- Tax fields
- Tax reports
- Tax configuration screens

## Technology

### Backend
- Python
- FastAPI
- SQLAlchemy 2
- PostgreSQL
- asyncpg
- JWT authentication
- Pydantic

### Frontend
- React
- TypeScript
- Vite
- React Router
- Professional dark POS UI

### Deployment
- Railway
- PostgreSQL
- Docker

## Currency

Default currency:

PKR

The currency is configurable through application settings.

## Timezone

Default timezone:

Asia/Karachi

## Project Structure

```text
Pos-system/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── security.py
│       ├── dependencies.py
│       ├── models/
│       ├── schemas/
│       ├── services/
│       ├── routers/
│       ├── reports/
│       ├── printing/
│       └── utils/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
