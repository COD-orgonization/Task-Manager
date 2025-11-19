import sqlite3
import uuid
import os
from typing import List, Optional, Tuple

class DataBase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.dirname(os.path.realpath(__file__)) + '/base.db'
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        
        self._check_and_create_tables()

    def __del__(self):
        if hasattr(self, 'connection'):
            self.connection.close()

    def _check_and_create_tables(self):
        self.cursor.execute('''
            SELECT name FROM sqlite_master WHERE type="table" AND name='Users'
        ''')
        
        if not self.cursor.fetchall():
            self.create_db()

    def create_db(self):
        try:
            # Создание таблицы пользователей
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users(
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL           
                )
            ''')
            
            # Создание таблицы досок
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Boards(
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    section TEXT
                )
            ''')
            
            # Создание таблицы задач
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Tasks(
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    executor TEXT
                )
            ''')
            
            # Соединение пользователя и доски
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS UserBoards(
                    idUsers TEXT,
                    idBoard TEXT,
                    FOREIGN KEY (idUsers) REFERENCES Users(id),
                    FOREIGN KEY (idBoard) REFERENCES Boards(id)
                )
            ''')
            
            # Соединение досок и задач
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS BorderTasks(
                    idBoard TEXT,
                    idTask TEXT,
                    FOREIGN KEY (idBoard) REFERENCES Boards(id),
                    FOREIGN KEY (idTask) REFERENCES Tasks(id)
                )
            ''')
            
            # Создание индексов для улучшения производительности
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_userboards_user ON UserBoards(idUsers)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_userboards_board ON UserBoards(idBoard)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_bordertasks_board ON BorderTasks(idBoard)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_bordertasks_task ON BorderTasks(idTask)')
            
            self.connection.commit()
            
        except sqlite3.Error as e:
            self.connection.rollback()
            raise e

    # ================= Пользователь ===============
    def add_user_db(self, user_id: str, username: str) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO Users (id, username) VALUES (?, ?)
            ''', (user_id, username))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def get_all_users(self) -> Optional[Tuple]:
        try:
            self.cursor.execute('''
                SELECT id FROM Users
            ''')
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(e)
            return None

    def get_user(self, user_id: str) -> Optional[Tuple]:
        try:
            self.cursor.execute('''
                SELECT * FROM Users WHERE id = ?
            ''', (user_id,))
            return self.cursor.fetchone()
        except sqlite3.Error:
            return None

    # =============== Доска ========================
    def create_board(self, user_id: str, title: str, description: str = "") -> Optional[str]:
        try:
            board_id = uuid.uuid4().hex
            section = '["todo", "in-progress", "done"]'
            
            # Создаем доску
            self.cursor.execute('''
                INSERT INTO Boards (id, title, description, section) VALUES (?, ?, ?, ?)
            ''', (board_id, title, description, section,))
            
            # Связываем пользователя с доской
            self.cursor.execute('''
                INSERT INTO UserBoards (idUsers, idBoard) VALUES (?, ?)
            ''', (user_id, board_id))
            
            self.connection.commit()
            return board_id
        except sqlite3.Error as e:
            self.connection.rollback()
            return None
        
    def delete_board(self, board_id: str) -> bool:
        """Удаление доски и связанных данных"""
        try:
            # Удаляем связи пользователей с доской
            self.cursor.execute('DELETE FROM UserBoards WHERE idBoard = ?', (board_id,))
            
            # Получаем задачи связанные с доской
            self.cursor.execute('SELECT idTask FROM BorderTasks WHERE idBoard = ?', (board_id,))
            task_ids = [row[0] for row in self.cursor.fetchall()]
            
            # Удаляем связи задач с доской
            self.cursor.execute('DELETE FROM BorderTasks WHERE idBoard = ?', (board_id,))
            
            # Удаляем сами задачи
            if task_ids:
                placeholders = ','.join('?' * len(task_ids))
                self.cursor.execute(f'DELETE FROM Tasks WHERE id IN ({placeholders})', task_ids)
            
            # Удаляем доску
            self.cursor.execute('DELETE FROM Boards WHERE id = ?', (board_id,))
            
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def add_user_to_board(self, user_id: str, board_id: str) -> bool:
        try:
            # Проверяем, не прикреплен ли уже пользователь к доске
            self.cursor.execute('''
                SELECT COUNT(*) FROM UserBoards WHERE idUsers = ? AND idBoard = ?
            ''', (user_id, board_id))
            result = self.cursor.fetchone()
            
            if result and result[0] > 0:
                # Пользователь уже прикреплен к этой доске
                return False
            
            self.cursor.execute('''
                INSERT INTO UserBoards (idUsers, idBoard) VALUES (?, ?)
            ''', (user_id, board_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def remove_user_from_board(self, user_id: str, board_id: str) -> bool:
        try:
            self.cursor.execute('''
                DELETE FROM UserBoards WHERE idUsers = ? AND idBoard = ?
            ''', (user_id, board_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def get_all_boards_user(self, user_id: str) -> List[Tuple]:
        try:
            self.cursor.execute('''
                SELECT b.id, b.title, b.description, b.section 
                FROM Boards b
                JOIN UserBoards ub ON b.id = ub.idBoard
                WHERE ub.idUsers = ?
            ''', (user_id,))
            return self.cursor.fetchall()
        except sqlite3.Error:
            return []

    def get_count_users_on_board(self, board_id: str) -> int:
        try:
            self.cursor.execute('''
                SELECT COUNT(*) FROM UserBoards WHERE idBoard = ?
            ''', (board_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error:
            return 0

    def get_all_tasks_from_board(self, board_id: str) -> List[Tuple]:
        try:
            self.cursor.execute('''
                SELECT t.id, t.title, t.description, t.status, t.executor
                FROM Tasks t
                JOIN BorderTasks bt ON t.id = bt.idTask
                WHERE bt.idBoard = ?
            ''', (board_id,))
            return self.cursor.fetchall()
        except sqlite3.Error:
            return []

    # ============= Задачи ===================
    def create_task(self, board_id: str, title: str, description: str = "", status: str = "todo") -> Optional[str]:
        try:
            task_id = uuid.uuid4().hex
            
            # Создаем задачу
            self.cursor.execute('''
                INSERT INTO Tasks (id, title, description, status) VALUES (?, ?, ?, ?)
            ''', (task_id, title, description, status))
            
            # Связываем задачу с доской
            self.cursor.execute('''
                INSERT INTO BorderTasks (idBoard, idTask) VALUES (?, ?)
            ''', (board_id, task_id))
            
            self.connection.commit()
            return task_id
        except sqlite3.Error as e:
            self.connection.rollback()
            return None

    def remove_task(self, task_id: str) -> bool:
        try:
            # Удаляем связь задачи с доской
            self.cursor.execute('DELETE FROM BorderTasks WHERE idTask = ?', (task_id,))
            
            # Удаляем саму задачу
            self.cursor.execute('DELETE FROM Tasks WHERE id = ?', (task_id,))
            
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def update_task_title(self, task_id: str, new_title: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET title = ? WHERE id = ?
            ''', (new_title, task_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def update_task_description(self, task_id: str, new_description: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET description = ? WHERE id = ?
            ''', (new_description, task_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET status = ? WHERE id = ?
            ''', (new_status, task_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def update_task(self, task_id: str, new_title: str, new_description: str, new_status: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET title = ?, description = ?, status = ? WHERE id = ?
            ''', (new_title, new_description, new_status, task_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def add_executor_to_task(self, task_id: str, user_id: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET executor = ? WHERE id = ?
            ''', (user_id, task_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def remove_executor_from_task(self, task_id: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET executor = NULL WHERE id = ?
            ''', (task_id,))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def update_executor_on_task(self, task_id: str, new_user_id: str) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Tasks SET executor = ? WHERE id = ?
            ''', (new_user_id, task_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def get_task(self, task_id: str) -> Optional[Tuple]:
        try:
            self.cursor.execute('''
                SELECT * FROM Tasks WHERE id = ?
            ''', (task_id,))
            return self.cursor.fetchone()
        except sqlite3.Error:
            return None

# Тестирование
if __name__ == "__main__":
    base = DataBase()
    
    # Тестовые данные
    base.add_user_db("0", "UserA")
    base.add_user_db("1", "UserB")
    base.add_user_db("2", "UserC")
    
    # Создание досок
    board1_id = base.create_board("0", "Project Board 1", "Main project board")
    board2_id = base.create_board("1", "Project Board 2", "Secondary board")
    
    if board1_id:
        print(f"Created board: {board1_id}")
        
        # Добавление пользователя на доску
        base.add_user_to_board("1", board1_id)

        # Проверяем чтобы не было дубликатов
        base.add_user_to_board("1", board1_id) 
        
        # Создание задачи
        task_id = base.create_task(board1_id, "Implement feature", "Create new functionality", "in-progress")

    
    # Получение досок пользователя
    user_boards = base.get_all_boards_user("0")
    print(f"User 0 boards: {user_boards}")
    
    user_boards = base.get_all_boards_user("1")
    print(f"User 1 boards: {user_boards}")