from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import traceback
import pytz
from typing import Optional, List

import firestore_service as fs
from config import firebase_config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}\n{traceback.format_exc()}")
        
        if isinstance(e, HTTPException):
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": str(e.detail)}
            )
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. Please try again later.",
                "error": str(e) if app.debug else None
            }
        )

# Dependency to get current user from session
async def get_current_user(request: Request):
    try:
        user_id = request.cookies.get("user_id")
        if not user_id:
            return None
        
        user = fs.get_user(user_id)
        if not user:
            return None
        
        return {"id": user_id, **user}
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/boards", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "firebase_config": firebase_config}
    )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html", 
        {"request": request, "firebase_config": firebase_config}
    )

@app.get("/boards", response_class=HTMLResponse)
async def boards_page(request: Request, user = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        logger.debug(f"Loading boards for user: {user['id']}")
        
        # Get boards created by the user
        owned_boards = fs.get_boards_created_by_user(user["id"])
        logger.debug(f"Found {len(owned_boards)} owned boards")
        
        # Get boards where user is a member
        member_boards = fs.get_boards_user_is_member_of(user["id"])
        logger.debug(f"Found {len(member_boards)} member boards")
        
        # Filter out boards that the user owns to avoid duplication
        member_boards = [
            board for board in member_boards 
            if board["created_by"] != user["id"]
        ]
        
        return templates.TemplateResponse(
            "boards.html",
            {
                "request": request,
                "user": user,
                "owned_boards": owned_boards,
                "member_boards": member_boards,
                "firebase_config": firebase_config
            }
        )
    except Exception as e:
        logger.error(f"Error in boards_page: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading boards")

@app.get("/boards/{board_id}", response_class=HTMLResponse)
async def board_detail(
    request: Request,
    board_id: str,
    user = Depends(get_current_user)
):
    try:
        if not user:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

        # Get board details
        board = fs.get_board(board_id)
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")

        # Check if user is a member of the board
        if user["id"] not in board["members"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get all board members' details
        member_details = []
        for member_id in board["members"]:
            member_info = fs.get_user(member_id)
            if member_info:
                member_details.append({
                    "id": member_id,
                    "email": member_info.get("email", "Unknown"),
                    "display_name": member_info.get("display_name", member_info.get("email", "Unknown").split("@")[0]),
                    "is_owner": member_id == board["created_by"]
                })

        # Get all tasks for the board
        tasks = fs.get_tasks_for_board(board_id)

        return templates.TemplateResponse(
            "board_detail.html",
            {
                "request": request,
                "user": user,
                "board": board,
                "tasks": tasks,
                "members": member_details,
                "is_owner": user["id"] == board["created_by"],
                "firebase_config": firebase_config
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing board details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/boards/create")
async def create_board(
    board_name: str = Form(...),
    user = Depends(get_current_user)
):
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not board_name.strip():
            raise HTTPException(status_code=400, detail="Board name cannot be empty")
        
        board_data = {
            "name": board_name.strip(),
            "created_by": user["id"],
            "members": [user["id"]],
            "created_at": datetime.now()
        }
        
        fs.create_board(board_data)
        return RedirectResponse(url="/boards", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        logger.error(f"Error creating board: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating board")

@app.post("/boards/{board_id}/add-task")
async def add_task(
    board_id: str,
    title: str = Form(...),
    due_date: str = Form(...),
    assigned_to: Optional[List[str]] = Form(None),
    user = Depends(get_current_user)
):
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        board = fs.get_board(board_id)
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")
        
        if user["id"] not in board["members"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check for duplicate task names
        existing_tasks = fs.get_tasks_for_board(board_id)
        if any(task["title"] == title.strip() for task in existing_tasks):
            raise HTTPException(status_code=400, detail="A task with this name already exists")
        
        due_date_dt = datetime.fromisoformat(due_date)
        
        task_data = {
            "title": title.strip(),
            "due_date": due_date_dt,
            "assigned_to": assigned_to if assigned_to else [],
            "completed": False,
            "created_by": user["id"],
            "created_at": datetime.now()
        }
        
        fs.create_task(board_id, task_data)
        return RedirectResponse(url=f"/boards/{board_id}", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding task: {str(e)}")
        raise HTTPException(status_code=500, detail="Error adding task")

@app.post("/boards/{board_id}/tasks/{task_id}/edit")
async def edit_task_route(
    board_id: str,
    task_id: str,
    request: Request,
    user = Depends(get_current_user)
):
    try:
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )

        # Get board details
        board = fs.get_board(board_id)
        if not board:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Board not found"}
            )

        # Check if user is a member of the board
        if user["id"] not in board["members"]:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Access denied"}
            )

        # Get form data
        form_data = await request.form()
        
        # Parse due date
        due_date_str = form_data.get("due_date")
        try:
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.error(f"Date parsing error: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid due date format"}
            )

        # Prepare task data
        task_data = {
            "title": form_data.get("title", "").strip(),
            "description": form_data.get("description", "").strip(),
            "due_date": due_date,
            "assigned_to": form_data.getlist("assigned_to"),
            "last_modified": datetime.now(pytz.UTC)
        }

        # Validate task data
        if not task_data["title"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Task title is required"}
            )

        # Update the task
        fs.update_task(board_id, task_id, task_data)

        return JSONResponse(
            content={
                "success": True,
                "message": "Task updated successfully",
                "task": {
                    "id": task_id,
                    "title": task_data["title"],
                    "description": task_data["description"],
                    "due_date": task_data["due_date"].isoformat(),
                    "assigned_to": task_data["assigned_to"]
                }
            }
        )

    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.post("/boards/{board_id}/tasks/{task_id}/toggle-complete")
async def toggle_task_complete(
    board_id: str,
    task_id: str,
    completed: bool = Form(...),
    user = Depends(get_current_user)
):
    try:
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )

        # Get the board and verify user's access
        board = fs.get_board(board_id)
        if not board:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Board not found"}
            )

        if user["id"] not in board["members"]:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Access denied"}
            )

        # Update task completion status
        fs.mark_task_complete(board_id, task_id, completed)

        return JSONResponse(
            content={
                "success": True,
                "message": "Task status updated successfully",
                "completed": completed,
                "completed_at": datetime.now().isoformat() if completed else None
            }
        )

    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Failed to update task status"}
        )

@app.post("/boards/{board_id}/rename")
async def rename_board(
    board_id: str,
    new_name: str = Form(...),
    user = Depends(get_current_user)
):
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        board = fs.get_board(board_id)
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")
        
        if board["created_by"] != user["id"]:
            raise HTTPException(status_code=403, detail="Only the board creator can rename the board")
        
        fs.update_board(board_id, {"name": new_name.strip()})
        return RedirectResponse(url=f"/boards/{board_id}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        logger.error(f"Error renaming board: {str(e)}")
        raise HTTPException(status_code=500, detail="Error renaming board")

@app.post("/boards/{board_id}/delete")
async def delete_board(
    board_id: str,
    user = Depends(get_current_user)
):
    try:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        board = fs.get_board(board_id)
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")
        
        if board["created_by"] != user["id"]:
            raise HTTPException(status_code=403, detail="Only the board creator can delete the board")
        
        # Check for non-owner members
        if len(board["members"]) > 1:
            raise HTTPException(status_code=400, detail="Remove all members before deleting the board")
        
        # Check for existing tasks
        tasks = fs.get_tasks_for_board(board_id)
        if tasks:
            raise HTTPException(status_code=400, detail="Remove all tasks before deleting the board")
        
        fs.delete_board(board_id)
        return RedirectResponse(url="/boards", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting board: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting board")

@app.post("/boards/{board_id}/add-user")
async def add_user_to_board(
    board_id: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    try:
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )

        # Get form data
        form_data = await request.form()
        user_email = form_data.get("user_email")

        if not user_email:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Email is required"}
            )

        # Get board details
        board = fs.get_board(board_id)
        if not board:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Board not found"}
            )

        # Verify current user is the board owner
        if board["created_by"] != user["id"]:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Only board owner can add users"}
            )

        # Get or create user by email
        new_user = fs.get_or_create_user_by_email(user_email)
        if not new_user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Could not create or find user with email {user_email}"}
            )

        # Check if user is already a member
        if new_user["uid"] in board.get("members", []):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "User is already a member of this board"}
            )

        # Add user to board
        fs.add_user_to_board(board_id, new_user["uid"])

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "User added successfully",
                "user": {
                    "id": new_user["uid"],
                    "email": new_user["email"],
                    "display_name": new_user.get("display_name", new_user["email"].split("@")[0])
                }
            }
        )

    except Exception as e:
        logger.error(f"Error adding user to board: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.post("/api/create-user")
async def create_user(request: Request):
    try:
        data = await request.json()
        user_id = data.get("uid")
        email = data.get("email")
        display_name = data.get("displayName")
        
        if not all([user_id, email]):
            raise HTTPException(status_code=400, detail="Missing required user information")
        
        user_data = {
            "email": email,
            "display_name": display_name if display_name else email.split("@")[0],
            "created_at": datetime.now()
        }
        
        fs.create_or_update_user(user_id, user_data)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating user")
    
@app.post("/boards/{board_id}/remove-user/{user_id}")
async def remove_user_from_board(
    board_id: str,
    user_id: str,
    user = Depends(get_current_user)
):
    try:
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )

        # Get board details
        board = fs.get_board(board_id)
        if not board:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Board not found"}
            )

        # Verify current user is the board owner
        if board["created_by"] != user["id"]:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Only board owner can remove users"}
            )

        # Cannot remove the board owner
        if user_id == board["created_by"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Cannot remove the board owner"}
            )

        # Check if user is a member
        if user_id not in board["members"]:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "User is not a member of this board"}
            )

        # Remove user's assignments from tasks
        tasks = fs.get_tasks_for_board(board_id)
        for task in tasks:
            if user_id in task.get("assigned_to", []):
                fs.update_task_assignments(board_id, task["id"], user_id, remove=True)

        # Remove user from board
        fs.remove_user_from_board(board_id, user_id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "User removed successfully"
            }
        )

    except Exception as e:
        logger.error(f"Error removing user from board: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Error removing user from board"}
        )
    
@app.post("/boards/{board_id}/tasks/{task_id}/delete")
async def delete_task_route(
    board_id: str,
    task_id: str,
    user = Depends(get_current_user)
):
    try:
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )

        # Get board details
        board = fs.get_board(board_id)
        if not board:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Board not found"}
            )

        # Check if user is a member of the board
        if user["id"] not in board["members"]:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Access denied"}
            )

        # Delete the task
        fs.delete_task(board_id, task_id)

        return JSONResponse(
            content={
                "success": True,
                "message": "Task deleted successfully"
            }
        )

    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Failed to delete task"}
        )

@app.post("/boards/{board_id}/tasks/{task_id}/edit")
async def edit_task_route(
    board_id: str,
    task_id: str,
    request: Request,
    user = Depends(get_current_user)
):
    try:
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Authentication required"}
            )

        # Get board details
        board = fs.get_board(board_id)
        if not board:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Board not found"}
            )

        # Check if user is a member of the board
        if user["id"] not in board["members"]:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Access denied"}
            )

        # Get form data
        form_data = await request.form()
        task_data = {
            "title": form_data.get("title"),
            "description": form_data.get("description"),
            "due_date": form_data.get("due_date"),
            "assigned_to": form_data.getlist("assigned_to"),
            "last_modified": datetime.now()
        }

        # Validate task data
        if not task_data["title"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Task title is required"}
            )

        # Update the task
        fs.update_task(board_id, task_id, task_data)

        return JSONResponse(
            content={
                "success": True,
                "message": "Task updated successfully",
                "task": {
                    "id": task_id,
                    **task_data
                }
            }
        )

    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Failed to update task"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)