from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from typing import List, Optional
from DB.mainDB import DataBase

app = FastAPI()
base = DataBase()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],#["http://127.0.0.1:5500", "http://localhost:5500"],  # Разрешенные источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешенные методы (GET, POST, etc.)
    allow_headers=["*"],  # Разрешенные заголовки
)

# Модели данных
class UserCreate(BaseModel):
    username: str

class BoardCreate(BaseModel):
    title: str
    description: Optional[str] = ""

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "todo"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class SectionCreate(BaseModel):
    title: str

# ==================== Пользователи ====================

@app.post("/api/users/{user_id}")
def create_user(user_id: str, user_data: UserCreate):
    success = base.add_user_db(user_id, user_data.username)
    if not success:
        raise HTTPException(status_code=400, detail="User already exists or invalid data")
    return {"message": "User created successfully"}

@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    user = base.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user[0],
        "username": user[1]
    }

@app.get("/api/users")
def get_all_users():
    users = base.get_all_users()
    return {"users": users}

# ==================== Доски ====================

@app.post("/api/boards/{user_id}")
def create_board(user_id: str, board_data: BoardCreate):
    board_id = base.create_board(user_id, board_data.title, board_data.description)
    if not board_id:
        raise HTTPException(status_code=400, detail="Failed to create board")
    return {"board_id": board_id}

@app.delete("/api/boards/{board_id}")
def delete_board(board_id: str):
    success = base.delete_board(board_id)
    if not success:
        raise HTTPException(status_code=404, detail="Board not found or deletion failed")
    return {"message": "Board deleted successfully"}

@app.post("/api/boards/{board_id}/add/user/{user_id}")
def add_user_to_board(board_id: str, user_id: str):
    success = base.add_user_to_board(user_id, board_id)
    if not success:
        raise HTTPException(status_code=400, detail="User already on board or invalid data")
    return {"message": "User added to board successfully"}

@app.delete("/api/boards/{board_id}/remove/user/{user_id}")
def remove_user_from_board(board_id: str, user_id: str):
    success = base.remove_user_from_board(user_id, board_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found on board")
    return {"message": "User removed from board successfully"}

@app.get("/api/home/{user_id}")
def get_all_boards_user(user_id: str):
    boards = base.get_all_boards_user(user_id)
    return {
        "data": [
            {
                "id": board[0],
                "title": board[1],
                "description": board[2],
                "section": board[3]
            }
            for board in boards
        ]
    }

@app.get("/api/boards/{board_id}/users/count")
def get_users_count_on_board(board_id: str):
    count = base.get_count_users_on_board(board_id)
    return {"board_id": board_id, "users_count": count}

# ==================== Секции ====================
@app.get("/api/boards/{board_id}/sections")
def get_all_sections_board(board_id: str):
    """Получить все секции для указанной доски"""
    sections = base.get_all_sections_board(board_id)
    return {
        "sections": [section[0] for section in sections]
    }

@app.post("/api/boards/{board_id}/sections")
def create_section(board_id: str, section_data: SectionCreate):
    """Создать секцию и связать ее с доской"""
    success = base.create_section(board_id, section_data.title)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create section")
    return {"message": "Section created successfully"}

@app.put("/api/boards/{board_id}/sections/{old_title}")
def update_section(board_id: str, old_title : str, section_data: SectionCreate):
    """Обновить название секции на доске"""
    success = base.update_section(board_id, old_title, section_data.title)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update section")
    return {"message": "Section updated successfully"}

@app.delete("/api/boards/{board_id}/sections/{section_title}")
def delete_section_from_board(board_id: str, section_title: str):
    """Удалить секцию с конкретной доски"""
    success = base.delete_section_from_board(board_id, section_title)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete section")
    return {"message": "Section deleted successfully"}

# ==================== Задачи ====================

@app.post("/api/boards/{board_id}/task")
def create_task(board_id: str, task_data: TaskCreate):
    task_id = base.create_task(board_id, task_data.title, task_data.description, task_data.status)
    if not task_id:
        raise HTTPException(status_code=400, detail="Failed to create task")
    return {"task_id": task_id}

@app.get("/api/board/{board_id}")
def get_all_tasks_from_board(board_id: str):
    tasks = base.get_all_tasks_from_board(board_id)
    return {
        "data": [
            {
                "id": task[0],
                "title": task[1],
                "description": task[2],
                "status": task[3],
                "executor": task[4]
            }
            for task in tasks
        ]
    }

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    task = base.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task[0],
        "title": task[1],
        "description": task[2],
        "status": task[3],
        "executor": task[4]
    }

@app.put("/api/tasks/{task_id}")
def update_task(task_id: str, task_data: TaskUpdate):
    # Проверяем, существует ли задача
    existing_task = base.get_task(task_id)
    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Используем существующие значения, если новые не предоставлены
    title = task_data.title if task_data.title is not None else existing_task[1]
    description = task_data.description if task_data.description is not None else existing_task[2]
    status = task_data.status if task_data.status is not None else existing_task[3]
    
    success = base.update_task(task_id, title, description, status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update task")
    return {"message": "Task updated successfully"}

@app.patch("/api/tasks/{task_id}/title")
def update_task_title(task_id: str, title_data: dict):
    if "title" not in title_data:
        raise HTTPException(status_code=400, detail="Title is required")
    
    success = base.update_task_title(task_id, title_data["title"])
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task title updated successfully"}

@app.patch("/api/tasks/{task_id}/description")
def update_task_description(task_id: str, description_data: dict):
    if "description" not in description_data:
        raise HTTPException(status_code=400, detail="Description is required")
    
    success = base.update_task_description(task_id, description_data["description"])
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task description updated successfully"}

@app.patch("/api/tasks/{task_id}/status")
def update_task_status(task_id: str, status_data: dict):
    if "status" not in status_data:
        raise HTTPException(status_code=400, detail="Status is required")
    
    success = base.update_task_status(task_id, status_data["status"])
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task status updated successfully"}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    success = base.remove_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# ==================== Исполнители задач ====================

@app.post("/api/tasks/{task_id}/executor/{user_id}")
def add_executor_to_task(task_id: str, user_id: str):
    success = base.add_executor_to_task(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Executor added to task successfully"}

@app.put("/api/tasks/{task_id}/executor/{user_id}")
def update_executor_on_task(task_id: str, user_id: str):
    success = base.update_executor_on_task(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Executor updated successfully"}

@app.delete("/api/tasks/{task_id}/executor")
def remove_executor_from_task(task_id: str):
    success = base.remove_executor_from_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Executor removed from task successfully"}

# ==================== Корневой эндпоинт ====================

@app.get("/")
def root():
    """Корневой эндпоинт с информацией о API"""
    return {
        "message": "Task Board API",
        "endpoints": {
            "users": {
                "create": "POST /api/users/{user_id}",
                "get": "GET /api/users/{user_id}",
                "get_all": "GET /api/users"
            },
            "boards": {
                "create": "POST /api/boards/{user_id}",
                "delete": "DELETE /api/boards/{board_id}",
                "add_user": "POST /api/boards/{board_id}/users/{user_id}",
                "remove_user": "DELETE /api/boards/{board_id}/users/{user_id}",
                "get_user_boards": "GET /api/home/{user_id}",
                "get_users_count": "GET /api/boards/{board_id}/users/count",
                "get_tasks": "GET /api/board/{board_id}"
            },
            "sections": {
                "get_all": "GET /api/boards/{board_id}/sections",
                "create": "POST /api/boards/{board_id}/sections",
                "update": "PUT /api/boards/{board_id}/sections",
                "delete": "DELETE /api/boards/{board_id}/sections/{section_title}"
            },
            "tasks": {
                "create": "POST /api/boards/{board_id}/tasks",
                "get": "GET /api/tasks/{task_id}",
                "update": "PUT /api/tasks/{task_id}",
                "delete": "DELETE /api/tasks/{task_id}",
                "update_title": "PATCH /api/tasks/{task_id}/title",
                "update_description": "PATCH /api/tasks/{task_id}/description",
                "update_status": "PATCH /api/tasks/{task_id}/status"
            },
            "executors": {
                "add": "POST /api/tasks/{task_id}/executor/{user_id}",
                "update": "PUT /api/tasks/{task_id}/executor/{user_id}",
                "remove": "DELETE /api/tasks/{task_id}/executor"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)