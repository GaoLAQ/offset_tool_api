# Offset Tool API

A comprehensive Django-based API for managing carbon offset calculations and environmental projects.

## Features

- 🔐 **Authentication & Authorization**: Token-based authentication system
- 📊 **Project Management**: Create and manage environmental projects
- 🧮 **Offset Calculations**: Calculate carbon, energy, and water offsets
- 📈 **Analytics**: Track progress and generate reports
- 🚀 **RESTful API**: Clean, well-documented API endpoints
- 🐳 **Docker Support**: Easy deployment with Docker and Docker Compose
- 📝 **Admin Interface**: Django admin for data management

## Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL
- **Cache/Queue**: Redis, Celery
- **Deployment**: Gunicorn, Docker
- **Frontend**: Bootstrap 5, Font Awesome

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Docker (optional)

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd offset_tool_api
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   For Windows (SQLite - recommended for development):

   ```bash
   pip install -r requirements-sqlite.txt
   ```

   For Windows (PostgreSQL - requires PostgreSQL installed):

   ```bash
   pip install -r requirements-windows.txt
   ```

   For Linux/Mac (PostgreSQL):

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**

   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**

   ```bash
   python manage.py migrate
   python manage.py create_superuser
   python manage.py seed_data  # Optional: Add sample data
   ```

6. **Run the server**
   ```bash
   python manage.py runserver
   ```

### Docker Setup

1. **Build and run with Docker Compose**

   ```bash
   docker-compose up --build
   ```

2. **Access the application**
   - API: http://localhost:8000/api/v1/
   - Admin: http://localhost:8000/admin/
   - Health Check: http://localhost:8000/health/

## API Endpoints

### CAD Offset Utility

- `POST /offset` - Upload a CAD file and offset its points along their normals.

The endpoint expects a `multipart/form-data` payload with the following fields:

| Field   | Type    | Description                                           |
| ------- | ------- | ----------------------------------------------------- |
| `file`  | File    | CAD point export containing position and normal data. |
| `offset`| Numeric | The offset distance to apply along each normal.       |

Two text-based formats are supported for rapid prototyping:

1. **JSON**

   ```json
   {
     "points": [
       {"position": [0, 0, 0], "normal": [0, 0, 1]},
       {"position": [1.5, 2.0, -0.5], "normal": [1, 0, 0]}
     ]
   }
   ```

2. **Plain text / CSV**

   One point per line in the order `x y z nx ny nz` where values can be separated by
   spaces, commas, or semicolons:

   ```text
   0 0 0 0 0 1
   1.5,2.0,-0.5,1,0,0
   ```

The response returns the offset coordinates:

```json
{
  "offset_points": [
    [0.0, 0.0, 2.5],
    [3.5, 2.0, -0.5]
  ]
}
```

## Data Models

### User

- Custom user model with email authentication
- Additional fields: phone, created_at, updated_at

### Project

- Project management with owner relationship
- Fields: name, description, owner, is_active

### OffsetCalculation

- Calculation tracking with multiple types
- Types: carbon, energy, water
- Fields: project, calculation_type, baseline_value, offset_value, unit, calculation_date, notes

## Development

### Running Tests

```bash
python manage.py test
```

### Creating Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Custom Management Commands

- `python manage.py create_superuser` - Create superuser with default credentials
- `python manage.py seed_data` - Seed database with sample data

### Code Style

```bash
# Format code
black .
isort .

# Lint code
flake8 .
```

## Configuration

### Environment Variables

| Variable      | Description       | Default                    |
| ------------- | ----------------- | -------------------------- |
| `SECRET_KEY`  | Django secret key | Required                   |
| `DEBUG`       | Debug mode        | `True`                     |
| `DB_NAME`     | Database name     | `offset_tool_db`           |
| `DB_USER`     | Database user     | `postgres`                 |
| `DB_PASSWORD` | Database password | `password`                 |
| `DB_HOST`     | Database host     | `localhost`                |
| `DB_PORT`     | Database port     | `5432`                     |
| `REDIS_URL`   | Redis URL         | `redis://127.0.0.1:6379/1` |

## Deployment

### Production Checklist

1. Set `DEBUG=False` in environment
2. Configure proper `SECRET_KEY`
3. Set up proper database credentials
4. Configure static file serving
5. Set up SSL/TLS certificates
6. Configure logging
7. Set up monitoring

### Environment-specific Settings

The project uses `python-decouple` for environment configuration. Create a `.env` file with your production settings.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, email support@example.com or create an issue in the repository.
