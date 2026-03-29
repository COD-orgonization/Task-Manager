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

        # Включение поддержки внешних ключей
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
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
                    description TEXT
                )
            ''')

            # Создание таблицы секций
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Sections(
                    title TEXT PRIMARY KEY
                )
            ''')
            
            # Создание таблицы задач
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Tasks(
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    executor TEXT,
                    FOREIGN KEY (status) REFERENCES Sections(title) ON DELETE SET NULL
                )
            ''')
            
            # Соединение пользователя и доски
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS UserBoards(
                    idUsers TEXT,
                    idBoard TEXT,
                    FOREIGN KEY (idUsers) REFERENCES Users(id) ON DELETE CASCADE,
                    FOREIGN KEY (idBoard) REFERENCES Boards(id) ON DELETE CASCADE
                )
            ''')

            # Соединение секции и доски
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS SectionBoards(
                    sectionTitle TEXT,
                    idBoard TEXT,
                    FOREIGN KEY (sectionTitle) REFERENCES Sections(title) ON DELETE CASCADE,
                    FOREIGN KEY (idBoard) REFERENCES Boards(id) ON DELETE CASCADE
                )
            ''')
            
            # Соединение досок и задач
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS BorderTasks(
                    idBoard TEXT,
                    idTask TEXT,
                    FOREIGN KEY (idBoard) REFERENCES Boards(id) ON DELETE CASCADE,
                    FOREIGN KEY (idTask) REFERENCES Tasks(id) ON DELETE CASCADE
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
            
            # Создаем доску
            self.cursor.execute('''
                INSERT INTO Boards (id, title, description) VALUES (?, ?, ?)
            ''', (board_id, title, description,))
            
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
            # Получаем задачи связанные с доской
            self.cursor.execute('SELECT idTask FROM BorderTasks WHERE idBoard = ?', (board_id,))
            task_ids = [row[0] for row in self.cursor.fetchall()]
            
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

    def update_board_title(self, board_id, new_title) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Boards SET title = ? WHERE id = ?
            ''', (new_title, board_id))
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def update_board_discription(self, board_id, new_discription) -> bool:
        try:
            self.cursor.execute('''
                UPDATE Boards SET description = ? WHERE id = ?
            ''', (new_discription, board_id))
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
                SELECT b.id, b.title, b.description 
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

    # ============= Секции ===================
    def get_all_sections_board(self, board_id: str) -> List[Tuple]:
        """Получить все секции для указанной доски"""
        try:
            self.cursor.execute('''
                SELECT sectionTitle 
                FROM SectionBoards 
                WHERE idBoard = ?
            ''', (board_id,))

            return self.cursor.fetchall()
        except sqlite3.Error:
            return []

    def create_section(self, board_id: str, title: str) -> tuple[bool, str]:
        """Создать секцию и связать ее с доской"""
        try:
            # Проверяем, существует ли уже такая связь секции с доской
            self.cursor.execute('''
                SELECT 1 FROM SectionBoards 
                WHERE sectionTitle = ? AND idBoard = ?
            ''', (title, board_id))
            
            if self.cursor.fetchone():
                return False, "Section already exists for this board"
            
            # Сначала добавляем секцию в таблицу Sections, если ее еще нет
            self.cursor.execute('''
                INSERT OR IGNORE INTO Sections (title) VALUES (?)
            ''', (title,))
            
            # Связываем секцию с доской
            self.cursor.execute('''
                INSERT INTO SectionBoards (sectionTitle, idBoard) VALUES (?, ?)
            ''', (title, board_id))
            
            self.connection.commit()
            return True, "Section created successfully"
        except sqlite3.Error as e:
            self.connection.rollback()
            return False, f"Database error: {str(e)}"

    def update_section(self, board_id: str, oldTitle: str, newTitle: str) -> bool:
        """Обновить название секции на доске"""
        try:
            # Сначала добавляем новую секцию, если ее нет
            self.cursor.execute('''
                INSERT OR IGNORE INTO Sections (title) VALUES (?)
            ''', (newTitle,))
            
            # Обновляем связь секции с доской
            self.cursor.execute('''
                UPDATE SectionBoards 
                SET sectionTitle = ? 
                WHERE idBoard = ? AND sectionTitle = ?
            ''', (newTitle, board_id, oldTitle))
            
            # Обновляем статусы задач, которые ссылались на старую секцию
            self.cursor.execute('''
                UPDATE Tasks 
                SET status = ? 
                WHERE status = ? AND id IN (
                    SELECT bt.idTask 
                    FROM BorderTasks bt 
                    WHERE bt.idBoard = ?
                )
            ''', (newTitle, oldTitle, board_id))
            
            # Удаляем старую секцию, если она больше нигде не используется
            self.cursor.execute('''
                DELETE FROM Sections 
                WHERE title = ? AND NOT EXISTS (
                    SELECT 1 FROM SectionBoards WHERE sectionTitle = ?
                )
            ''', (oldTitle, oldTitle))
            
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    def delete_section_from_board(self, board_id: str, title: str) -> bool:
        """Удалить секцию с конкретной доски"""
        try:
            # Удаляем связь секции с доской
            self.cursor.execute('''
                DELETE FROM SectionBoards 
                WHERE idBoard = ? AND sectionTitle = ?
            ''', (board_id, title))
            
            # Удаляем саму секцию, если она больше нигде не используется
            self.cursor.execute('''
                DELETE FROM Sections 
                WHERE title = ? AND NOT EXISTS (
                    SELECT 1 FROM SectionBoards WHERE sectionTitle = ?
                )
            ''', (title, title))
            
            # Удаляем задачи, которые ссылались на эту секцию на этой доске
            self.cursor.execute('''
                Delete from Tasks 
                WHERE status = ? AND id IN (
                    SELECT bt.idTask 
                    FROM BorderTasks bt 
                    WHERE bt.idBoard = ?
                )
            ''', (title, board_id))
            
            self.connection.commit()
            return True
        except sqlite3.Error:
            self.connection.rollback()
            return False

    # ============= Задачи ===================
    def create_task(self, board_id: str, title: str, description: str, status: str) -> Optional[str]:
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
        
        # Тестирование работы с секциями
        base.create_section(board1_id, "todo")
        base.create_section(board1_id, "in-progress")
        base.create_section(board1_id, "done")

        base.create_section(board1_id, "todo")

                # Создание задачи
        task_id = base.create_task(board1_id, "Implement feature", "Create new functionality", "in-progress")
        print(f"Задачи ${board1_id}: ${base.get_all_tasks_from_board(board1_id)}")
        
        # Получение секций доски
        sections = base.get_all_sections_board(board1_id)
        print(f"Board sections: {sections}")
        
        # Обновление секции
        base.create_section(board2_id, "todo")
        base.update_section(board2_id, "todo", "backlog")
        
        # Получение обновленных секций
        sections_updated = base.get_all_sections_board(board2_id)
        print(f"Updated board sections: {sections_updated}")
    
    # Получение досок пользователя
    user_boards = base.get_all_boards_user("0")
    print(f"User 0 boards: {user_boards}")
    
    user_boards = base.get_all_boards_user("1")
    print(f"User 1 boards: {user_boards}")
    
    # Тестирование удаления секции
    if board2_id:
        print(base.get_all_sections_board(board2_id))
        base.create_section(board2_id, "test-section")
        print(base.get_all_sections_board(board2_id))
        base.delete_section_from_board(board2_id, "test-section")
        print("Section deletion tested")
        print(base.get_all_sections_board(board2_id))