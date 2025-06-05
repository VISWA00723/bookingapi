# Fitness Studio Booking API

A simple REST API for managing fitness class bookings built with Python, Flask, and SQLite.

## Features

- **Persistent Storage**: SQLite database for data persistence
- View upcoming fitness classes with available slots
- Book a spot in a class
- View all bookings by email address
- Timezone-aware scheduling (IST/UTC)
- Input validation and error handling
- Logging for all operations
- Thread-safe database operations

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Database Schema

The application uses SQLite with the following tables:

### fitness_classes
- `id` (Integer, Primary Key): Unique identifier for the class
- `name` (String): Name of the class (e.g., "Yoga", "Zumba")
- `datetime_ist` (DateTime): Class start time in IST
- `datetime_utc` (DateTime): Class start time in UTC
- `instructor` (String): Name of the instructor
- `total_slots` (Integer): Maximum number of slots
- `available_slots` (Integer): Current available slots
- `duration_minutes` (Integer): Duration of the class in minutes

### bookings
- `id` (String, Primary Key): Unique booking ID (UUID)
- `class_id` (Integer, Foreign Key): Reference to fitness_classes.id
- `client_name` (String): Name of the client
- `client_email` (String): Email of the client (indexed for faster lookups)
- `booking_time` (DateTime): When the booking was made (UTC)

## Setup

### Database Initialization

The database will be automatically created and initialized with sample data when you first run the application. The database file will be created at `instance/fitness_studio.db`.

1. **Clone the repository** (if applicable)

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   # source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```
   The API will be available at `http://localhost:5000`

### Database Management

- The database is automatically created when you first run the application
- The database file is stored at `instance/fitness_studio.db`
- To reset the database, simply delete the `instance` directory and restart the application

### Sample Data

The application comes with the following sample classes pre-loaded:
- Yoga (7:00 AM IST, 15 slots)
- Zumba (6:30 PM IST, 20 slots)
- HIIT (8:00 AM IST, 12 slots)
- Yoga (7:00 AM IST next day, 15 slots)

## API Endpoints

### 1. Get Available Classes

- **URL**: `GET /classes`
- **Description**: Returns a list of all upcoming fitness classes
- **Response**:
  ```json
  [
    {
      "id": 1,
      "name": "Yoga",
      "datetime_ist": "2025-06-10T07:00:00+05:30",
      "datetime_utc": "2025-06-10T01:30:00+00:00",
      "instructor": "Priya Sharma",
      "available_slots": 15,
      "total_slots": 15,
      "duration_minutes": 60
    },
    ...
  ]
  ```

### 2. Book a Class

- **URL**: `POST /book`
- **Description**: Book a spot in a fitness class
- **Request Body**:
  ```json
  {
    "class_id": 1,
    "client_name": "John Doe",
    "client_email": "john@example.com"
  }
  ```
- **Success Response (201)**:
  ```json
  {
    "message": "Booking successful",
    "booking_id": "550e8400-e29b-41d4-a716-446655440000",
    "class_name": "Yoga",
    "class_datetime_ist": "2025-06-10T07:00:00+05:30",
    "available_slots": 14
  }
  ```
- **Error Responses**:
  - 400: Missing or invalid fields
  - 404: Class not found
  - 409: No available slots

### 3. Get Bookings by Email

- **URL**: `GET /bookings?email=user@example.com`
- **Description**: Get all bookings for a specific email address
- **Response**:
  ```json
  [
    {
      "booking_id": "550e8400-e29b-41d4-a716-446655440000",
      "class_id": 1,
      "class_name": "Yoga",
      "class_datetime_ist": "2025-06-10T07:00:00+05:30",
      "client_name": "John Doe",
      "client_email": "john@example.com",
      "booking_time": "2025-06-05T15:30:00+05:30"
    }
  ]
  ```

## Timezone Handling

- All class times are stored in IST (Indian Standard Time, UTC+5:30)
- The API returns both IST and UTC times for clarity
- Bookings are checked against the current UTC time to prevent booking past classes

## Error Handling

The API returns appropriate HTTP status codes and JSON error messages for various scenarios:
- 400 Bad Request: Invalid or missing parameters
- 404 Not Found: Requested resource not found
- 409 Conflict: Business rule violation (e.g., no available slots)
- 500 Internal Server Error: Unexpected server error

## Logging

All operations are logged with timestamps for auditing and debugging purposes. Logs are output to the console.




