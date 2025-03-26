# GOST Formatter Integration

This project integrates a GOST document formatter API with a Java backend service.

## Getting Started

### Environment Setup

Before starting the application, you need to set up environment variables:

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and replace the placeholder values with your actual credentials:
   ```
   # Database credentials
   POSTGRES_AUTH_PASSWORD=your_secure_password
   POSTGRES_DOC_PASSWORD=your_secure_password

   # MinIO credentials
   MINIO_ROOT_USER=your_minio_username
   MINIO_ROOT_PASSWORD=your_secure_minio_password
   ```

### Running the Application

Start all services using Docker Compose:

```bash
docker-compose up -d
```

To rebuild specific services:

```bash
docker-compose build gost-formatter-api gost-kafka-listener
docker-compose up -d
```

## Architecture

The application consists of:

- **Java Auth Service**: User authentication
- **Java Doc Service**: Document management
- **GOST Formatter API**: Formats documents according to GOST standards
- **Kafka**: Message broker for service communication
- **MinIO**: S3-compatible object storage for document files
- **PostgreSQL**: Database for user and document metadata

## API Endpoints

The GOST Formatter API is available at:

- `POST http://localhost:5000/api/format` - Format a document
- `GET http://localhost:5000/api/health` - Health check
- `GET http://localhost:5000/api/info` - API documentation

## Security Notes

- Never commit the `.env` file to version control
- Always use environment variables for credentials
- For production deployment, consider using a secrets management solution 