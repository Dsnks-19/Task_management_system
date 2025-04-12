from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, validator

class User(BaseModel):
    """User model for storing user information."""
    uid: str = Field(..., description="Firebase user ID")
    email: EmailStr = Field(..., description="User's email address")
    display_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="User's display name"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified: datetime = Field(default_factory=datetime.now)

    @validator('display_name', pre=True, always=True)
    def set_display_name(cls, v, values):
        """Set display name to email prefix if not provided."""
        if not v and 'email' in values:
            return values['email'].split('@')[0]
        return v

    class Config:
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Task(BaseModel):
    """Task model for storing task information."""
    id: Optional[str] = Field(None, description="Task ID from Firestore")
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Task title"
    )
    due_date: datetime = Field(..., description="Task due date")
    assigned_to: List[str] = Field(
        default_factory=list,
        description="List of user IDs assigned to the task"
    )
    completed: bool = Field(
        default=False,
        description="Task completion status"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when task was completed"
    )
    created_by: str = Field(
        ...,
        description="User ID of task creator"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when task was created"
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when task was last modified"
    )

    @validator('due_date')
    def validate_due_date(cls, v):
        """Validate that due date is not in the past."""
        if v < datetime.now():
            raise ValueError("Due date cannot be in the past")
        return v

    @validator('completed_at')
    def validate_completed_at(cls, v, values):
        """Validate completed_at timestamp."""
        if values.get('completed', False):
            if not v:
                return datetime.now()
        else:
            if v:
                return None
        return v

    class Config:
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TaskBoard(BaseModel):
    """Task board model for storing board information."""
    id: Optional[str] = Field(None, description="Board ID from Firestore")
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Board name"
    )
    created_by: str = Field(
        ...,
        description="User ID of board creator"
    )
    members: List[str] = Field(
        default_factory=list,
        description="List of user IDs who are members of the board"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when board was created"
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when board was last modified"
    )

    @validator('members')
    def creator_must_be_member(cls, v, values):
        """Ensure board creator is always a member."""
        if 'created_by' in values and values['created_by'] not in v:
            v.append(values['created_by'])
        return v

    @validator('name')
    def validate_board_name(cls, v):
        """Validate board name format."""
        if not v.strip():
            raise ValueError("Board name cannot be empty")
        return v.strip()

    class Config:
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TaskStats(BaseModel):
    """Model for task statistics."""
    total_tasks: int = Field(
        default=0,
        ge=0,
        description="Total number of tasks"
    )
    active_tasks: int = Field(
        default=0,
        ge=0,
        description="Number of active (incomplete) tasks"
    )
    completed_tasks: int = Field(
        default=0,
        ge=0,
        description="Number of completed tasks"
    )
    unassigned_tasks: int = Field(
        default=0,
        ge=0,
        description="Number of unassigned tasks"
    )

    @validator('active_tasks', 'completed_tasks', 'unassigned_tasks')
    def validate_counts(cls, v, values):
        """Ensure counts don't exceed total tasks."""
        if 'total_tasks' in values and v > values['total_tasks']:
            raise ValueError("Count cannot exceed total tasks")
        return v

class BoardMember(BaseModel):
    """Model for board member information."""
    id: str = Field(..., description="User ID")
    display_name: str = Field(..., description="User's display name")
    email: EmailStr = Field(..., description="User's email")
    is_owner: bool = Field(
        default=False,
        description="Whether the member is the board owner"
    )
    joined_at: datetime = Field(
        default_factory=datetime.now,
        description="When the member joined the board"
    )

    class Config:
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def create_task_from_dict(data: dict) -> Task:
    """Create a Task instance from a dictionary."""
    if isinstance(data.get('due_date'), str):
        data['due_date'] = datetime.fromisoformat(data['due_date'])
    if isinstance(data.get('completed_at'), str):
        data['completed_at'] = datetime.fromisoformat(data['completed_at'])
    return Task(**data)

def create_board_from_dict(data: dict) -> TaskBoard:
    """Create a TaskBoard instance from a dictionary."""
    if isinstance(data.get('created_at'), str):
        data['created_at'] = datetime.fromisoformat(data['created_at'])
    if isinstance(data.get('last_modified'), str):
        data['last_modified'] = datetime.fromisoformat(data['last_modified'])
    return TaskBoard(**data)