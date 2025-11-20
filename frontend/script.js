// Основные функции навигации
function showPage(pageId) {
    // Скрываем все страницы
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
    });
    
    // Показываем нужную страницу
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
    }
}

// Хранение данных
let boards = [];
let currentBoardId = null;
let currentUserId = "0"; // Замените на реальный ID пользователя

// Базовый URL API
const API_BASE_URL = 'http://localhost:8000/api';

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    loadUserBoards();
});

async function loadUserBoards() {
    try {
        const response = (await fetch(`${API_BASE_URL}/home/${currentUserId}`));
        let data = await response.json();

        boards = data.data || [];
        console.log(data)

        updateBoardsList();
    } catch (error) {
        console.error('Failed to load boards:', error);
    }
}

// Функции для работы с досками
function updateBoardsList() {
    const boardsList = document.getElementById('boards-list');
    const noBoardsMessage = document.getElementById('no-boards-message');
    const boardListElement = document.querySelector('.board-list');
    
    if (boards.length === 0) {
        boardsList.classList.add('hidden');
        noBoardsMessage.classList.remove('hidden');
    } else {
        boardsList.classList.remove('hidden');
        noBoardsMessage.classList.add('hidden');
        
        // Очищаем список
        boardListElement.innerHTML = '';
        
        // Заполняем список досок
        boards.forEach(board => {
            const listItem = document.createElement('li');
            listItem.className = 'board-item';
            listItem.innerHTML = `
                <div class="board-info">
                    <h3>${board.title}</h3>
                    <p>${board.description}</p>
                </div>
            `;
            listItem.addEventListener("click", ()=>{openBoard(board.id);});

            boardListElement.appendChild(listItem);
        });
    }
}

async function createNewBoard() {
    const name = document.getElementById('board-name').value.trim();
    const description = document.getElementById('board-description').value.trim();
    
    if (!name) {
        alert('Введите название доски');
        return;
    }

    let newBoard = {
        title: name,
        description: description,
        sections: null
    };

    const response = await fetch(`${API_BASE_URL}/boards/${currentUserId}`, {
        method: 'POST',
        headers: {
            "Content-type": "application/json"
        },
        body: JSON.stringify(newBoard)
    });

    const data = await response.json();

    newBoard = {
        id : data.board_id,
        title: name,
        description: description,
        sections: NaN
    };
    
    boards.push(newBoard);
    updateBoardsList();
    showPage('home-page');
    
    // Очищаем форму
    document.getElementById('board-name').value = '';
    document.getElementById('board-description').value = '';
}

// Функция для открытия доски и загрузки задач
async function openBoard(boardId, boardTitle) {
    currentBoardId = boardId;
    
    try {
        const board = boards.find(b => b.id === boardId);
        const responseTask = await fetch(`${API_BASE_URL}/board/${boardId}`);
        let data = await responseTask.json();
        const tasks = data.data;
        console.log(tasks)

        const responseSection = await await fetch(`${API_BASE_URL}/board/${boardId}/sections`);
        data = await responseSection.json();
        const sections = data.data;
        
        // Обновляем заголовок страницы доски
        document.querySelector('#board-page h1').textContent = boardTitle;
        
        // Очищаем контейнер разделов
        const pageContent = document.querySelector('#board-page .page-content');
        pageContent.innerHTML = '';
        
        // Группируем задачи по статусам
        const tasksByStatus = {};
        sections.forEach(section => { tasksByStatus[section] = []; });
        tasks.forEach(task => { 
            if(tasksByStatus[task.status])
                tasksByStatus[task.status].push(task); 
        });
        
        // Создаем разделы для каждого статуса
        Object.keys(tasksByStatus).forEach(status => {
            const section = createBoardSection(status, tasksByStatus[status], currentBoardId);
            pageContent.appendChild(section);
        });

        //loadBoardSettings(board)
        showPage('board-page');
    } catch (error) {
        console.error('Ошибка при загрузке задач:', error);
    }
}

// Функция создания раздела доски с задачами
function createBoardSection(status, tasks, board_id) {
    const section = document.createElement('div');
    section.className = 'board-section';
    
    var str = `<div class="section-title-with-button">
            <h3 class="section-title">${status}</h3>
            <button class="add-task-button">
                <img src="img/plus2.png" alt="Добавить" class="icon">
            </button>
        </div>
        <div class="tasks-container">`;
    
    for(task in tasks){
        str += `${tasks.map(task => 
                `<div class="task-item" dataTaskId="${task.id}">
                    <input type="text" class="task-input" value="${task.title}">
                    <button class="delete-task-button">⨯</button>
                </div>
            `).join('')}`
    }
    str += "</div>"

    section.innerHTML = str;
    
    const addButton = section.querySelector('.add-task-button');
    addButton.addEventListener('click', function() {
        addTask(this, status, board_id);
    });

    section.querySelectorAll('.delete-task-button').forEach(button => {
        button.addEventListener('click', function() {
            deleteTask(this);
        });
    });

    section.querySelectorAll('.task-input').forEach(input => {
        input.addEventListener('blur', function() {
            saveTask(this);
        });
    });

    return section;
}

// Функции для работы с задачами
async function addTask(button, status, board_id) {
    const tasksContainer = button.closest('.board-section').querySelector('.tasks-container');

    const newTask = {
        title: "Новая задача",
        description: "",
        status: status 
    }

    const response = await fetch(`${API_BASE_URL}/boards/${board_id}/task`, {
        method: 'POST',
        headers: {
            "Content-type": "application/json"
        },
        body: JSON.stringify(newTask)
    });
    const data = await response.json();
    newTask['id'] = data.task_id;
    console.log(newTask)

    const taskElement = document.createElement('div');
    taskElement.className = 'task-item';
    taskElement.innerHTML = `
        <input type="text" class="task-input" placeholder="Новая задача" onblur="saveTask(this, 111, 222)">
        <button class="delete-task-button" onclick="deleteTask(this, 111, 222)">⨯</button>
    `;
    tasksContainer.appendChild(taskElement);
}

async function deleteTask(button) {
    const taskElement = button.closest('.task-item');
    const taskId = taskElement.getAttribute('datataskid');
    taskElement.remove();

    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: 'DELETE',
        headers: {
            "Content-type": "application/json"
        }
    });
}

async function saveTask(input) {
    const taskElement = input.closest('.task-item');
    const taskId = taskElement.getAttribute('datataskid');

    if(input.value == ""){
        alert("Название не может быть пустым")
        input.value = "Задача"
    }
    const newTitle = input.value;
    await fetch(`${API_BASE_URL}/tasks/${taskId}/title`, {
        method: 'PATCH',
        headers: {
            "Content-type": "application/json-patch+json"
        },
        body: JSON.stringify({title: newTitle})
    });
}


// Функции для настроек доски
function loadBoardSettings(board) {
    if (!board) return;
    
    // Загружаем основные настройки
    const settingsInputs = document.querySelectorAll('#settings-page .form-input, #settings-page .form-textarea');
    settingsInputs[0].value = board.title;
    settingsInputs[1].value = board.description;
    
    // Загружаем разделы
    const sectionsList = document.getElementById('sections-list');
    sectionsList.innerHTML = '';
    
    const sections = JSON.parse(board.section);
    sections.forEach(section => {
        const sectionItem = document.createElement('li');
        sectionItem.className = 'section-item';
        sectionItem.innerHTML = `
            <input type="text" class="section-input" value="${section}" onchange="updateSectionName(${section}, this.value)">
            <button class="delete-button" onclick="deleteSection(this, ${section})">⨯</button>
        `;
        sectionsList.appendChild(sectionItem);
    });
}

function saveBoardSettings() {
    const board = boards.find(b => b.id === currentBoardId);
    if (!board) return;
    
    // Сохраняем основные настройки
    const settingsInputs = document.querySelectorAll('#settings-page .form-input, #settings-page .form-textarea');
    board.name = settingsInputs[0].value.trim();
    board.description = settingsInputs[1].value.trim();
    
    // Обновляем заголовок на странице доски
    document.querySelector('#board-page h1').textContent = board.name;
    
    saveBoardsToStorage();
    showPage('board-page');
}

function addNewSection() {
    const board = boards.find(b => b.id === currentBoardId);
    if (!board) return;
    
    const newSectionId = Date.now();
    const newSection = {
        id: newSectionId,
        name: `Раздел ${board.sections.length + 1}`,
        tasks: []
    };
    
    board.sections.push(newSection);
    
    // Добавляем в UI
    const sectionsList = document.getElementById('sections-list');
    const sectionItem = document.createElement('li');
    sectionItem.className = 'section-item';
    sectionItem.innerHTML = `
        <input type="text" class="section-input" value="${newSection.name}" onchange="updateSectionName(${newSectionId}, this.value)">
        <button class="delete-button" onclick="deleteSection(this, ${newSectionId})">⨯</button>
    `;
    sectionsList.appendChild(sectionItem);
    
    saveBoardsToStorage();
}

function updateSectionName(sectionId, newName) {
    const board = boards.find(b => b.id === currentBoardId);
    const section = board.sections.find(s => s.id === sectionId);
    
    if (section) {
        section.name = newName.trim();
        saveBoardsToStorage();
        
        // Обновляем на странице доски
        const sectionTitle = document.querySelector(`[data-section-id="${sectionId}"]`).closest('.board-section').querySelector('.section-title');
        if (sectionTitle) {
            sectionTitle.textContent = newName;
        }
    }
}

function deleteSection(button) {
    const board = boards.find(b => b.id === currentBoardId);
    
    // Не позволяем удалить последний раздел
    if (board.sections.length <= 1) {
        alert('Нельзя удалить последний раздел');
        return;
    }
    
    // Удаляем из данных
    board.sections = board.sections.filter(s => s.id !== sectionId);
    
    // Удаляем из UI
    button.closest('.section-item').remove();
    
    saveBoardsToStorage();
}