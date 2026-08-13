"""Student API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.student import Student
from app.schemas import (
    StudentCreate, StudentResponse, StudentImportRequest,
    StudentDetailResponse
)

router = APIRouter()


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    """Create a new student."""
    # Check for duplicate stable_id
    existing = db.query(Student).filter(
        Student.stable_id == student.stable_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Student with this stable_id already exists"
        )
    
    db_student = Student(**student.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.post("/import", response_model=List[StudentResponse])
def import_students(
    import_request: StudentImportRequest,
    db: Session = Depends(get_db)
):
    """Bulk import students from CSV data."""
    created = []
    for student_data in import_request.students:
        # Check for duplicates
        existing = db.query(Student).filter(
            Student.stable_id == student_data.stable_id
        ).first()
        if not existing:
            db_student = Student(
                stable_id=student_data.stable_id,
                first_name=student_data.first_name,
                course_id=import_request.course_id if hasattr(import_request, 'course_id') else 1
            )
            db.add(db_student)
            created.append(db_student)
    
    db.commit()
    for student in created:
        db.refresh(student)
    return created


@router.get("/", response_model=List[StudentResponse])
def list_students(
    course_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List students, optionally filtered by course."""
    query = db.query(Student)
    if course_id:
        query = query.filter(Student.course_id == course_id)
    students = query.offset(skip).limit(limit).all()
    return students


@router.get("/{student_id}", response_model=StudentDetailResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Get a specific student with details."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    """Delete a student (cascades to consents, voiceprints, etc.)."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.delete(student)
    db.commit()
    return None
