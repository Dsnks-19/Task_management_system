// Task management functionality
document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const addTaskForm = document.getElementById('add-task-form');
    const editTaskModal = document.getElementById('editTaskModal');
    const deleteTaskModal = document.getElementById('deleteTaskModal');
    const editTaskForm = document.getElementById('edit-task-form');

    // Initialize date inputs with current date and time
    function initializeDateInputs() {
        const now = new Date();
        const nowStr = now.toISOString().slice(0, 16);
        const dateInputs = document.querySelectorAll('input[type="datetime-local"]');
        dateInputs.forEach(input => {
            if (!input.value) {  // Only set if not already set
                input.value = nowStr;
            }
            input.min = nowStr; // Prevent past dates
        });
    }

    // Task validation
    function validateTask(title, dueDate) {
        const errors = [];
        
        // Title validation
        if (!title || title.trim().length === 0) {
            errors.push("Task title cannot be empty");
        }
        if (title.trim().length > 100) {
            errors.push("Task title cannot exceed 100 characters");
        }

        // Due date validation
        if (!dueDate) {
            errors.push("Due date is required");
            return errors;
        }

        const dueDateObj = new Date(dueDate);
        const now = new Date();
        if (dueDateObj < now) {
            errors.push("Due date cannot be in the past");
        }

        return errors;
    }

    // Show error message
    function showError(message, duration = 5000) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
        errorDiv.style.zIndex = '1050';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(errorDiv);

        setTimeout(() => {
            errorDiv.classList.remove('show');
            setTimeout(() => errorDiv.remove(), 150);
        }, duration);
    }

    // Add new task form handler
    if (addTaskForm) {
        addTaskForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const title = this.querySelector('[name="title"]').value;
            const dueDate = this.querySelector('[name="due_date"]').value;

            const errors = validateTask(title, dueDate);
            if (errors.length > 0) {
                showError(errors.join('<br>'));
                return;
            }

            // Check for duplicate task names
            const existingTasks = Array.from(document.querySelectorAll('.task-card'))
                .map(task => task.querySelector('.card-title').textContent.trim());
            
            if (existingTasks.includes(title.trim())) {
                showError("A task with this name already exists");
                return;
            }

            this.submit();
        });
    }

    // Edit Task Modal Handler
    if (editTaskModal) {
        const modalInstance = new bootstrap.Modal(editTaskModal);

        editTaskModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const taskId = button.getAttribute('data-task-id');
            const taskCard = document.querySelector(`.task-card[data-task-id="${taskId}"]`);
            
            if (!taskCard) {
                console.error('Task card not found:', taskId);
                return;
            }

            const form = this.querySelector('#edit-task-form');
            form.action = `/boards/${boardId}/tasks/${taskId}/edit`;
            
            // Populate form fields
            form.querySelector('#edit-task-title').value = taskCard.getAttribute('data-task-title');
            form.querySelector('#edit-task-description').value = taskCard.getAttribute('data-task-description') || '';
            
            // Handle due date
            const dueDate = taskCard.getAttribute('data-task-due-date');
            if (dueDate) {
                const date = new Date(dueDate);
                const formattedDate = date.toISOString().slice(0, 16);
                form.querySelector('#edit-task-due-date').value = formattedDate;
            }
            
            // Handle assigned users
            try {
                const assignedTo = JSON.parse(taskCard.getAttribute('data-task-assigned-to') || '[]');
                const selectElement = form.querySelector('#edit-task-assigned-to');
                Array.from(selectElement.options).forEach(option => {
                    option.selected = assignedTo.includes(option.value);
                });
            } catch (error) {
                console.error('Error parsing assigned users:', error);
            }
        });

        // Handle edit task form submission
        if (editTaskForm) {
            editTaskForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const submitButton = this.querySelector('button[type="submit"]');
                const errorDiv = document.getElementById('edit-task-error');
                const title = this.querySelector('#edit-task-title').value;
                const dueDate = this.querySelector('#edit-task-due-date').value;
                
                // Validate form
                const errors = validateTask(title, dueDate);
                if (errors.length > 0) {
                    errorDiv.textContent = errors.join('\n');
                    errorDiv.classList.remove('d-none');
                    return;
                }
                
                try {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
                    
                    const formData = new FormData(this);
                    
                    const response = await fetch(this.action, {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(data.message || `HTTP error! status: ${response.status}`);
                    }

                    if (!data.success) {
                        throw new Error(data.message || 'Failed to update task');
                    }

                    // Success - hide modal and reload page
                    modalInstance.hide();
                    window.location.reload();

                } catch (error) {
                    console.error('Error:', error);
                    errorDiv.textContent = error.message;
                    errorDiv.classList.remove('d-none');
                } finally {
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Save Changes';
                }
            });
        }
    }

    // Delete Task Modal Handler
    if (deleteTaskModal) {
        deleteTaskModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const taskId = button.getAttribute('data-task-id');
            const taskTitle = button.getAttribute('data-task-title');
            
            this.querySelector('#delete-task-title').textContent = taskTitle;
            const form = this.querySelector('#delete-task-form');
            form.action = `/boards/${boardId}/tasks/${taskId}/delete`;
        });

        const deleteTaskForm = document.getElementById('delete-task-form');
        if (deleteTaskForm) {
            deleteTaskForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const submitButton = this.querySelector('button[type="submit"]');
                const errorDiv = document.getElementById('delete-task-error');
                
                try {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';
                    
                    const response = await fetch(this.action, {
                        method: 'POST'
                    });

                    const data = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(data.message || `HTTP error! status: ${response.status}`);
                    }

                    if (!data.success) {
                        throw new Error(data.message || 'Failed to delete task');
                    }

                    window.location.reload();

                } catch (error) {
                    console.error('Error:', error);
                    errorDiv.textContent = error.message;
                    errorDiv.classList.remove('d-none');
                } finally {
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Delete Task';
                }
            });
        }
    }

    // Task completion toggle handler
    function setupTaskCompletionToggle() {
        document.querySelectorAll('form[action*="/toggle-complete"]').forEach(form => {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                try {
                    const response = await fetch(this.action, {
                        method: 'POST',
                        body: new FormData(this)
                    });

                    const data = await response.json();
                    
                    if (!response.ok || !data.success) {
                        throw new Error(data.message || 'Failed to update task status');
                    }

                    // Update UI and reload to show new status
                    updateTaskCounters();
                    window.location.reload();
                    
                } catch (error) {
                    console.error('Error:', error);
                    showError('Failed to update task status');
                }
            });
        });
    }

    // Update task counters
    function updateTaskCounters() {
        const tasks = document.querySelectorAll('.task-card');
        let activeCount = 0;
        let completedCount = 0;

        tasks.forEach(task => {
            if (task.classList.contains('task-completed')) {
                completedCount++;
            } else {
                activeCount++;
            }
        });

        const activeCounter = document.getElementById('active-tasks-count');
        const completedCounter = document.getElementById('completed-tasks-count');
        const totalCounter = document.getElementById('total-tasks-count');

        if (activeCounter) activeCounter.textContent = activeCount;
        if (completedCounter) completedCounter.textContent = completedCount;
        if (totalCounter) totalCounter.textContent = tasks.length;
    }

    // Initialize all features
    initializeDateInputs();
    setupTaskCompletionToggle();
    updateTaskCounters();
});

// Make updateTaskCounters available globally
window.updateTaskCounters = function() {
    const tasks = document.querySelectorAll('.task-card');
    let activeCount = 0;
    let completedCount = 0;

    tasks.forEach(task => {
        if (task.classList.contains('task-completed')) {
            completedCount++;
        } else {
            activeCount++;
        }
    });

    const activeCounter = document.getElementById('active-tasks-count');
    const completedCounter = document.getElementById('completed-tasks-count');
    const totalCounter = document.getElementById('total-tasks-count');

    if (activeCounter) activeCounter.textContent = activeCount;
    if (completedCounter) completedCounter.textContent = completedCount;
    if (totalCounter) totalCounter.textContent = tasks.length;
};