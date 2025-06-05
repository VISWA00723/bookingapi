import os
import sys
import pytest
import json
from datetime import datetime, timedelta
import pytz

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import app, db, FitnessClass, Booking, UTC, IST

# Test configuration
TEST_DB = 'test_fitness_studio.db'

@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{TEST_DB}'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Add test data
            add_test_data()
            
        yield client
        
        # Clean up after tests
        with app.app_context():
            db.session.remove()
            db.drop_all()
        
        # Remove the test database
        try:
            os.remove(TEST_DB)
        except OSError:
            pass

def add_test_data():
    """Add test data to the database."""
    # Add test classes
    now = datetime.now(IST)
    future = now + timedelta(days=1)
    past = now - timedelta(days=1)
    
    classes = [
        # Future class with available slots
        FitnessClass(
            name="Morning Yoga",
            datetime_ist=future.replace(hour=8, minute=0, second=0, microsecond=0),
            datetime_utc=(future.replace(hour=8, minute=0, second=0, microsecond=0).astimezone(UTC)),
            instructor="Priya Sharma",
            total_slots=10,
            available_slots=5,
            duration_minutes=60
        ),
        # Future class that's fully booked
        FitnessClass(
            name="Evening HIIT",
            datetime_ist=future.replace(hour=18, minute=0, second=0, microsecond=0),
            datetime_utc=(future.replace(hour=18, minute=0, second=0, microsecond=0).astimezone(UTC)),
            instructor="Rahul Verma",
            total_slots=10,
            available_slots=0,
            duration_minutes=45
        ),
        # Past class
        FitnessClass(
            name="Past Yoga",
            datetime_ist=past.replace(hour=10, minute=0, second=0, microsecond=0),
            datetime_utc=(past.replace(hour=10, minute=0, second=0, microsecond=0).astimezone(UTC)),
            instructor="Priya Sharma",
            total_slots=10,
            available_slots=3,
            duration_minutes=60
        )
    ]
    
    db.session.add_all(classes)
    db.session.commit()
    
    # Add a test booking
    booking = Booking(
        id="test-booking-123",
        class_id=1,  # Morning Yoga
        client_name="Test User",
        client_email="test@example.com",
        booking_time=datetime.now(UTC)
    )
    
    db.session.add(booking)
    db.session.commit()

def test_get_classes(client):
    """Test getting all upcoming classes."""
    response = client.get('/classes')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should only return future classes by default
    assert data['status'] == 'success'
    assert len(data['classes']) == 1  # Only one future class with available slots
    assert data['classes'][0]['name'] == "Morning Yoga"
    assert data['classes'][0]['is_available'] is True

def test_get_classes_include_past(client):
    """Test getting all classes including past ones."""
    response = client.get('/classes?include_past=true')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should return all classes including past ones
    assert data['status'] == 'success'
    assert len(data['classes']) == 3  # All test classes
    
    # Should be ordered by date (past first because include_past=true)
    assert data['classes'][0]['name'] == "Past Yoga"
    assert data['classes'][1]['name'] == "Morning Yoga"
    assert data['classes'][2]['name'] == "Evening HIIT"

def test_book_class_success(client):
    """Test successful class booking."""
    booking_data = {
        'class_id': 1,  # Morning Yoga
        'client_name': 'New User',
        'client_email': 'new.user@example.com'
    }
    
    response = client.post(
        '/book',
        data=json.dumps(booking_data),
        content_type='application/json'
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['message'] == 'Booking successful'
    assert data['available_slots'] == 4  # Was 5, now 4

def test_book_class_duplicate(client):
    """Test booking the same class twice with the same email."""
    booking_data = {
        'class_id': 1,  # Morning Yoga
        'client_name': 'Test User',
        'client_email': 'test@example.com'  # Already booked this class
    }
    
    response = client.post(
        '/book',
        data=json.dumps(booking_data),
        content_type='application/json'
    )
    
    assert response.status_code == 409
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'already booked' in data['message'].lower()

def test_book_class_full(client):
    """Test booking a fully booked class."""
    booking_data = {
        'class_id': 2,  # Evening HIIT (fully booked)
        'client_name': 'New User',
        'client_email': 'new.user@example.com'
    }
    
    response = client.post(
        '/book',
        data=json.dumps(booking_data),
        content_type='application/json'
    )
    
    assert response.status_code == 409
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'no available slots' in data['message'].lower()

def test_book_class_past(client):
    """Test booking a past class."""
    booking_data = {
        'class_id': 3,  # Past Yoga
        'client_name': 'New User',
        'client_email': 'new.user@example.com'
    }
    
    response = client.post(
        '/book',
        data=json.dumps(booking_data),
        content_type='application/json'
    )
    
    assert response.status_code == 409
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'already started' in data['message'].lower()

def test_get_bookings(client):
    """Test getting bookings for a user."""
    # Test user with existing booking
    response = client.get('/bookings?email=test@example.com')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert data['status'] == 'success'
    assert len(data['bookings']) == 1
    assert data['bookings'][0]['client_email'] == 'test@example.com'
    assert data['bookings'][0]['class_name'] == 'Morning Yoga'

def test_get_bookings_empty(client):
    """Test getting bookings for a user with no bookings."""
    response = client.get('/bookings?email=nonexistent@example.com')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert data['status'] == 'success'
    assert data['message'] == 'No bookings found for this email'
    assert len(data['bookings']) == 0

def test_invalid_email(client):
    """Test with invalid email format."""
    # Test invalid email in booking
    booking_data = {
        'class_id': 1,
        'client_name': 'Test User',
        'client_email': 'invalid-email'
    }
    
    response = client.post(
        '/book',
        data=json.dumps(booking_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'invalid email' in data['message'].lower()
    
    # Test missing email in bookings endpoint
    response = client.get('/bookings')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'email query parameter is required' in data['message'].lower()

if __name__ == '__main__':
    pytest.main(['-v', 'test_app.py'])
