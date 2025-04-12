from datetime import datetime
from typing import List, Dict, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Firestore client
from config import db

def get_user(user_id: str) -> Optional[Dict]:
    """Get user information from Firestore."""
    try:
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_data['id'] = user_doc.id  # Add the document ID as id field
            return user_data
        logger.warning(f"User {user_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise

def add_user_to_board(board_id: str, user_id: str) -> None:
    """Add a user to a board's members list."""
    try:
        # Get the board first to verify it exists
        board_ref = db.collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            raise ValueError(f"Board {board_id} not found")
        
        # Get current members
        board_data = board.to_dict()
        current_members = board_data.get('members', [])
        
        # Check if user is already a member
        if user_id in current_members:
            logger.info(f"User {user_id} is already a member of board {board_id}")
            return
            
        # Update the members array
        board_ref.update({
            "members": firestore.ArrayUnion([user_id]),
            "last_modified": datetime.now()
        })
        
        logger.info(f"User {user_id} added to board {board_id}")
        
    except Exception as e:
        logger.error(f"Error adding user {user_id} to board {board_id}: {str(e)}")
        raise
    """Get user information from Firestore."""
    try:
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            return user_doc.to_dict()
        logger.warning(f"User {user_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise

def create_or_update_user(user_id: str, user_data: Dict) -> None:
    """Create or update user data in Firestore."""
    try:
        # Add timestamp if not present
        if 'created_at' not in user_data:
            user_data['created_at'] = datetime.now()
        user_data['last_modified'] = datetime.now()
        
        db.collection('users').document(user_id).set(user_data, merge=True)
        logger.info(f"User {user_id} created/updated successfully")
    except Exception as e:
        logger.error(f"Error creating/updating user {user_id}: {str(e)}")
        raise

def get_boards_created_by_user(user_id: str) -> List[Dict]:
    """Get all boards created by the user."""
    try:
        boards = []
        logger.debug(f"Fetching boards created by user: {user_id}")
        
        # Query boards created by the user
        board_refs = db.collection('boards').where(
            filter=FieldFilter("created_by", "==", user_id)
        ).stream()
        
        for board_ref in board_refs:
            board_data = board_ref.to_dict()
            if not board_data:
                logger.warning(f"Empty board data for ID: {board_ref.id}")
                continue
                
            board_data['id'] = board_ref.id
            
            # Convert Firestore Timestamp to datetime
            if 'created_at' in board_data:
                if isinstance(board_data['created_at'], datetime):
                    pass
                elif hasattr(board_data['created_at'], 'timestamp'):
                    board_data['created_at'] = datetime.fromtimestamp(
                        board_data['created_at'].timestamp()
                    )
                else:
                    board_data['created_at'] = datetime.now()
            else:
                board_data['created_at'] = datetime.now()
            
            boards.append(board_data)
        
        logger.debug(f"Found {len(boards)} boards created by user {user_id}")
        return boards
        
    except Exception as e:
        logger.error(f"Error fetching boards for user {user_id}: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise

def get_boards_user_is_member_of(user_id: str) -> List[Dict]:
    """Get all boards where the user is a member."""
    try:
        boards = []
        logger.debug(f"Fetching boards where user {user_id} is a member")
        
        # Query boards where user is in members array
        board_refs = db.collection('boards').where(
            filter=FieldFilter("members", "array_contains", user_id)
        ).stream()
        
        for board_ref in board_refs:
            board_data = board_ref.to_dict()
            if not board_data:
                logger.warning(f"Empty board data for ID: {board_ref.id}")
                continue
                
            board_data['id'] = board_ref.id
            
            # Convert Firestore Timestamp to datetime
            if 'created_at' in board_data:
                if isinstance(board_data['created_at'], datetime):
                    pass
                elif hasattr(board_data['created_at'], 'timestamp'):
                    board_data['created_at'] = datetime.fromtimestamp(
                        board_data['created_at'].timestamp()
                    )
                else:
                    board_data['created_at'] = datetime.now()
            else:
                board_data['created_at'] = datetime.now()
            
            boards.append(board_data)
        
        logger.debug(f"Found {len(boards)} boards where user {user_id} is a member")
        return boards
        
    except Exception as e:
        logger.error(f"Error fetching member boards for user {user_id}: {str(e)}\nTraceback: {traceback.format_exc()}")
        raise

def create_board(board_data: Dict) -> str:
    """Create a new board and return its ID."""
    try:
        # Check for duplicate board names for this user
        existing_boards = db.collection('boards').where(
            filter=FieldFilter("created_by", "==", board_data["created_by"])
        ).where(
            filter=FieldFilter("name", "==", board_data["name"])
        ).limit(1).stream()
        
        if list(existing_boards):
            raise ValueError("A board with this name already exists")
        
        # Add timestamps
        board_data['created_at'] = datetime.now()
        board_data['last_modified'] = datetime.now()
        
        board_ref = db.collection('boards').document()
        board_ref.set(board_data)
        
        logger.info(f"Board created successfully: {board_ref.id}")
        return board_ref.id
    except Exception as e:
        logger.error(f"Error creating board: {str(e)}")
        raise

def get_board(board_id: str) -> Optional[Dict]:
    """Get a board by its ID."""
    try:
        board_doc = db.collection('boards').document(board_id).get()
        if not board_doc.exists:
            logger.warning(f"Board {board_id} not found")
            return None
        
        board_data = board_doc.to_dict()
        board_data['id'] = board_doc.id
        return board_data
    except Exception as e:
        logger.error(f"Error fetching board {board_id}: {str(e)}")
        raise

def update_board(board_id: str, board_data: Dict) -> None:
    """Update a board's data."""
    try:
        # Add last modified timestamp
        board_data['last_modified'] = datetime.now()
        db.collection('boards').document(board_id).update(board_data)
        logger.info(f"Board {board_id} updated successfully")
    except Exception as e:
        logger.error(f"Error updating board {board_id}: {str(e)}")
        raise

def delete_board(board_id: str) -> None:
    """Delete a board and all its tasks."""
    try:
        # Delete all tasks in the board
        tasks_ref = db.collection('boards').document(board_id).collection('tasks')
        delete_collection(tasks_ref, 100)
        # Delete the board
        db.collection('boards').document(board_id).delete()
        logger.info(f"Board {board_id} and its tasks deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting board {board_id}: {str(e)}")
        raise

def delete_collection(collection, batch_size):
    """Delete a collection in batches to avoid timeout."""
    try:
        docs = collection.limit(batch_size).stream()
        deleted = 0
        
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        
        if deleted >= batch_size:
            return delete_collection(collection, batch_size)
    except Exception as e:
        logger.error(f"Error deleting collection: {str(e)}")
        raise

def get_or_create_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by email or create if not exists."""
    try:
        # First, try to find the user by email
        users_ref = db.collection('users')
        query = users_ref.where(filter=FieldFilter("email", "==", email)).limit(1)
        users = list(query.stream())
        
        if users:
            # User exists
            user_data = users[0].to_dict()
            user_data['uid'] = users[0].id
            return user_data
            
        # User doesn't exist, create new user
        new_user_data = {
            "email": email,
            "display_name": email.split("@")[0],
            "created_at": datetime.now(),
            "last_modified": datetime.now()
        }
        
        # Add new user to Firestore
        new_user_ref = users_ref.document()
        new_user_ref.set(new_user_data)
        
        # Return the new user data with uid
        new_user_data['uid'] = new_user_ref.id
        logger.info(f"Created new user with email: {email}")
        return new_user_data
        
    except Exception as e:
        logger.error(f"Error in get_or_create_user_by_email: {str(e)}")
        raise

def add_user_to_board(board_id: str, user_id: str) -> None:
    """Add a user to a board's members list."""
    try:
        # Get the board first to verify it exists
        board_ref = db.collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            raise ValueError(f"Board {board_id} not found")
        
        # Get current members
        board_data = board.to_dict()
        current_members = board_data.get('members', [])
        
        # Check if user is already a member
        if user_id in current_members:
            logger.info(f"User {user_id} is already a member of board {board_id}")
            return
            
        # Update the members array and last modified timestamp
        board_ref.update({
            "members": firestore.ArrayUnion([user_id]),
            "last_modified": datetime.now()
        })
        
        logger.info(f"User {user_id} added to board {board_id}")
        
    except Exception as e:
        logger.error(f"Error adding user {user_id} to board {board_id}: {str(e)}")
        raise

def remove_user_from_board(board_id: str, user_id: str) -> None:
    """Remove a user from a board's members list."""
    try:
        board_ref = db.collection('boards').document(board_id)
        board_ref.update({
            "members": firestore.ArrayRemove([user_id]),
            "last_modified": datetime.now()
        })
        logger.info(f"User {user_id} removed from board {board_id}")
    except Exception as e:
        logger.error(f"Error removing user {user_id} from board {board_id}: {str(e)}")
        raise

def get_tasks_for_board(board_id: str) -> List[Dict]:
    """Get all tasks for a specific board."""
    try:
        tasks = []
        task_refs = db.collection('boards').document(board_id)\
                     .collection('tasks').stream()
        
        for task_ref in task_refs:
            task_data = task_ref.to_dict()
            task_data['id'] = task_ref.id
            # Ensure all required fields are present
            task_data.setdefault('completed', False)
            task_data.setdefault('assigned_to', [])
            task_data.setdefault('completed_at', None)
            tasks.append(task_data)
        
        return tasks
    except Exception as e:
        logger.error(f"Error fetching tasks for board {board_id}: {str(e)}")
        raise

def create_task(board_id: str, task_data: Dict) -> str:
    """Create a new task in a board and return its ID."""
    try:
        # Check for duplicate task names in this board
        existing_tasks = db.collection('boards').document(board_id)\
            .collection('tasks').where(
                filter=FieldFilter("title", "==", task_data["title"])
            ).limit(1).stream()
        
        if list(existing_tasks):
            raise ValueError("A task with this name already exists in this board")
        
        # Add timestamps
        task_data['created_at'] = datetime.now()
        task_data['last_modified'] = datetime.now()
        
        task_ref = db.collection('boards').document(board_id)\
                    .collection('tasks').document()
        task_ref.set(task_data)
        
        logger.info(f"Task created successfully in board {board_id}")
        return task_ref.id
    except Exception as e:
        logger.error(f"Error creating task in board {board_id}: {str(e)}")
        raise

def update_task(board_id: str, task_id: str, task_data: Dict) -> None:
    """Update a task's data."""
    try:
        # Add last modified timestamp
        task_data['last_modified'] = datetime.now()
        db.collection('boards').document(board_id)\
          .collection('tasks').document(task_id).update(task_data)
        logger.info(f"Task {task_id} updated successfully")
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {str(e)}")
        raise

def mark_task_complete(board_id: str, task_id: str, completed: bool) -> None:
    """Mark a task as complete or incomplete."""
    try:
        task_ref = db.collection('boards').document(board_id)\
                    .collection('tasks').document(task_id)
        
        update_data = {
            "completed": completed,
            "completed_at": datetime.now() if completed else None,
            "last_modified": datetime.now()
        }
        
        task_ref.update(update_data)
        logger.info(f"Task {task_id} completion status updated to {completed}")
    except Exception as e:
        logger.error(f"Error updating task completion status: {str(e)}")
        raise

def delete_task(board_id: str, task_id: str) -> None:
    """Delete a task from a board."""
    try:
        db.collection('boards').document(board_id)\
          .collection('tasks').document(task_id).delete()
        logger.info(f"Task {task_id} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {str(e)}")
        raise

def remove_user_from_board(board_id: str, user_id: str) -> None:
    """Remove a user from a board's members list."""
    try:
        # Get the board first to verify it exists
        board_ref = db.collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            raise ValueError(f"Board {board_id} not found")
            
        # Update the members array
        board_ref.update({
            "members": firestore.ArrayRemove([user_id]),
            "last_modified": datetime.now()
        })
        
        logger.info(f"User {user_id} removed from board {board_id}")
        
    except Exception as e:
        logger.error(f"Error removing user {user_id} from board {board_id}: {str(e)}")
        raise

def update_task_assignments(board_id: str, task_id: str, user_id: str, remove: bool = False) -> None:
    """Update task assignments when removing a user."""
    try:
        task_ref = db.collection('boards').document(board_id)\
                    .collection('tasks').document(task_id)
        
        # Get the task first to verify it exists
        task = task_ref.get()
        if not task.exists:
            raise ValueError(f"Task {task_id} not found in board {board_id}")
        
        task_data = task.to_dict()
        assigned_to = task_data.get("assigned_to", [])
        
        if remove:
            if user_id in assigned_to:
                task_ref.update({
                    "assigned_to": firestore.ArrayRemove([user_id]),
                    "last_modified": datetime.now()
                })
        else:
            if user_id not in assigned_to:
                task_ref.update({
                    "assigned_to": firestore.ArrayUnion([user_id]),
                    "last_modified": datetime.now()
                })
                
        logger.info(f"Task {task_id} assignments updated for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating task assignments: {str(e)}")
        raise