Nutrition API (Backend)
Backend service for Nutrition App.
Provides products catalog and detailed nutrition data based on USDA FoodData Central (Foundation dataset).

🚀 Tech Stack
Python 3.11+
Django
Django REST Framework
PostgreSQL (Docker)
drf-spectacular (OpenAPI 3.0 / Swagger)

Project Structure
config/                  → Django config
nutrition/               → Core app
nutrition/models.py      → Domain models
nutrition/serializers.py → API serializers
nutrition/views.py       → API views
nutrition/management/    → USDA import command
docker-compose.yml       → PostgreSQL container

Local Setup
git clone https://github.com/IvDyriv/nutrition-app-backend

Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Mac/Linux

pip install -r requirements.txt

Start PostgreSQL (Docker)
docker compose up -d

Apply migrations
python manage.py migrate

Import sample data
Download USDA Foundation dataset from:
https://fdc.nal.usda.gov/download-datasets.html
Foundation Foods

Place JSON file into:
/data/
Then run:
python manage.py import_usda_foundation --limit 50
For dry run:
python manage.py import_usda_foundation --limit 10 --dry-run

Run development server
python manage.py runserver

Base API URL
http://127.0.0.1:8000/api/v1/products/

API Documentation
Swagger UI:
http://127.0.0.1:8000/api/docs/

Available Endpoints (Stage 1)

GET /api/v1/products/
Products catalog
Supports pagination and search.

GET /api/v1/products/{id}/
Detailed product information including:
product info
list of nutrients
amount_per_100g
unit
