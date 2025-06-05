from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import datetime
import pytz
import uuid
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime as dt

# Initialize SQLAlchemy
db = SQLAlchemy()

# Define models
@dataclass
class FitnessClass(db.Model):
    __tablename__ = 'fitness_classes'
    
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), nullable=False)
    datetime_ist = db.Column(db.DateTime, nullable=False)
    datetime_utc = db.Column(db.DateTime, nullable=False)
    instructor: str = db.Column(db.String(100), nullable=False)
    total_slots: int = db.Column(db.Integer, nullable=False)
    available_slots: int = db.Column(db.Integer, nullable=False)
    duration_minutes: int = db.Column(db.Integer, nullable=False)
    
    # Relationship with bookings
    bookings = db.relationship('Booking', backref='fitness_class', lazy=True)

@dataclass
class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id: str = db.Column(db.String(36), primary_key=True)
    class_id: int = db.Column(db.Integer, db.ForeignKey('fitness_classes.id'), nullable=False)
    client_name: str = db.Column(db.String(100), nullable=False)
    client_email: str = db.Column(db.String(120), nullable=False, index=True)
    booking_time = db.Column(db.DateTime, nullable=False, default=dt.utcnow)

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Configure SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_studio.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database with the Flask app
    db.init_app(app)
    
    return app

app = create_app()

# Timezone configuration
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.utc

def add_class(class_id: int, name: str, year: int, month: int, day: int, 
             hour: int, minute: int, instructor: str, total_slots: int, 
             duration_minutes: int) -> bool:
    """
    Add a new fitness class with the given details.
    
    Args:
        class_id: Unique identifier for the class
        name: Name of the class (e.g., "Yoga", "Zumba")
        year, month, day, hour, minute: Class start time in IST
        instructor: Name of the instructor
        total_slots: Maximum number of available slots
        duration_minutes: Duration of the class in minutes
        
    Returns:
        bool: True if class was added successfully, False otherwise
    """
    try:
        # Create timezone-aware datetime in IST
        naive_dt = datetime.datetime(year, month, day, hour, minute)
        ist_dt = IST.localize(naive_dt)
        
        # Convert to UTC for storage
        utc_dt = ist_dt.astimezone(UTC)
        
        # Check if class with this ID already exists
        existing_class = FitnessClass.query.get(class_id)
        if existing_class:
            logging.warning(f"Class with ID {class_id} already exists")
            return False
        
        # Create new class
        new_class = FitnessClass(
            id=class_id,
            name=name,
            datetime_ist=ist_dt,
            datetime_utc=utc_dt,
            instructor=instructor,
            total_slots=total_slots,
            available_slots=total_slots,
            duration_minutes=duration_minutes
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        logging.info(f"Added class: {name} at {ist_dt} with {total_slots} slots")
        return True
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding class: {e}")
        return False

def add_sample_classes():
    """Add sample fitness classes to the database."""
    sample_classes = [
        (1, "Yoga", 2025, 6, 10, 7, 0, "Priya Sharma", 15, 60),
        (2, "Zumba", 2025, 6, 10, 18, 30, "Rahul Verma", 20, 45),
        (3, "HIIT", 2025, 6, 11, 8, 0, "Amit Singh", 12, 30),
        (4, "Yoga", 2025, 6, 12, 7, 0, "Priya Sharma", 15, 60)
    ]
    
    for cls in sample_classes:
        add_class(*cls)

# Initialize database with sample data
with app.app_context():
    db.create_all()
    if not FitnessClass.query.first():
        add_sample_classes()

@app.route('/classes', methods=['GET'])
def get_classes():
    """
    Get all upcoming fitness classes.
    Returns classes in JSON format with IST and UTC times.
    """
    now = datetime.datetime.now(UTC)
    
    # Query only future classes
    upcoming_classes = FitnessClass.query.filter(FitnessClass.datetime_utc > now).all()
    
    # Convert SQLAlchemy objects to dictionaries
    result = []
    for cls in upcoming_classes:
        result.append({
            'id': cls.id,
            'name': cls.name,
            'datetime_ist': cls.datetime_ist.isoformat(),
            'datetime_utc': cls.datetime_utc.isoformat(),
            'instructor': cls.instructor,
            'available_slots': cls.available_slots,
            'total_slots': cls.total_slots,
            'duration_minutes': cls.duration_minutes
        })
    
    return jsonify(result), 200

@app.route('/book', methods=['POST'])
def book_class():
    """
    Book a spot in a fitness class.
    
    Expected JSON payload:
    {
        "class_id": int,
        "client_name": str,
        "client_email": str
    }
    """
    data = request.get_json()
    
    # Input validation
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    class_id = data.get('class_id')
    client_name = data.get('client_name')
    client_email = data.get('client_email')
    
    if not all([class_id, client_name, client_email]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        class_id = int(class_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'class_id must be an integer'}), 400
    
    # Start a database transaction
    try:
        # Find the class with lock to prevent race conditions
        target_class = FitnessClass.query.with_for_update().get(class_id)
        if not target_class:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if class is in the future
        now = datetime.datetime.now(UTC)
        if target_class.datetime_utc <= now:
            return jsonify({'error': 'Cannot book a class that has already started or ended'}), 400
        
        # Check available slots
        if target_class.available_slots <= 0:
            return jsonify({'error': 'No available slots for this class'}), 409
        
        # Create booking
        booking_id = str(uuid.uuid4())
        new_booking = Booking(
            id=booking_id,
            class_id=class_id,
            client_name=client_name,
            client_email=client_email
        )
        
        # Update available slots
        target_class.available_slots -= 1
        
        # Save to database
        db.session.add(new_booking)
        db.session.commit()
        
        logging.info(f"Booking created: {booking_id} for class {class_id} by {client_email}")
        
        return jsonify({
            'message': 'Booking successful',
            'booking_id': booking_id,
            'class_name': target_class.name,
            'class_datetime_ist': target_class.datetime_ist.isoformat(),
            'available_slots': target_class.available_slots
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating booking: {e}")
        return jsonify({'error': 'An error occurred while processing your booking'}), 500

@app.route('/bookings', methods=['GET'])
def get_bookings():
    """
    Get all bookings for a specific email address.
    Query parameter: email (required)
    """
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email query parameter is required'}), 400
    
    try:
        # Query bookings for the given email (case-insensitive)
        client_bookings = Booking.query.filter(Booking.client_email.ilike(email)).all()
        
        # Format the response
        result = []
        for booking in client_bookings:
            result.append({
                'booking_id': booking.id,
                'class_id': booking.class_id,
                'class_name': booking.fitness_class.name,
                'class_datetime_ist': booking.fitness_class.datetime_ist.isoformat(),
                'client_name': booking.client_name,
                'client_email': booking.client_email,
                'booking_time': booking.booking_time.isoformat()
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        logging.error(f"Error retrieving bookings: {e}")
        return jsonify({'error': 'An error occurred while retrieving bookings'}), 500

if __name__ == '__main__':
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
