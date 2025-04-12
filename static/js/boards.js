document.addEventListener("DOMContentLoaded", function() {
    // Create board modal
    const createBoardModal = document.getElementById("createBoardModal");
    const createBoardBtn = document.getElementById("create-board-btn");
    const closeCreateBoardModal = document.getElementById("close-create-board-modal");
    
    // Form validation for board creation
    const createBoardForm = document.getElementById("create-board-form");
    if (createBoardForm) {
        createBoardForm.addEventListener("submit", function(e) {
            const boardName = document.getElementById("board-name").value.trim();
            
            // Check for empty board name
            if (!boardName) {
                e.preventDefault();
                showError("Board name cannot be empty");
                return;
            }

            // Check for duplicate board names
            const existingBoards = Array.from(document.querySelectorAll('.list-group-item'))
                .map(item => item.textContent.trim().split('Owner')[0].trim());
            
            if (existingBoards.includes(boardName)) {
                e.preventDefault();
                showError("A board with this name already exists");
                return;
            }

            // Check board name length
            if (boardName.length > 50) {
                e.preventDefault();
                showError("Board name cannot exceed 50 characters");
                return;
            }
        });
    }

    // Generic modal setup function
    function setupModal(modalId, openBtnId, closeBtnId) {
        const modal = document.getElementById(modalId);
        const openBtn = document.getElementById(openBtnId);
        const closeBtn = document.getElementById(closeBtnId);
        
        if (openBtn && modal) {
            openBtn.addEventListener("click", () => {
                modal.style.display = "block";
            });
        }
        
        if (closeBtn && modal) {
            closeBtn.addEventListener("click", () => {
                modal.style.display = "none";
            });
        }
        
        // Close when clicking outside
        window.addEventListener("click", (event) => {
            if (event.target === modal) {
                modal.style.display = "none";
            }
        });
    }

    // Error display function
    function showError(message, duration = 5000) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.role = 'alert';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert error message at the top of the content
        const container = document.querySelector('.container');
        container.insertBefore(errorDiv, container.firstChild);

        // Auto dismiss after duration
        setTimeout(() => {
            errorDiv.classList.remove('show');
            setTimeout(() => errorDiv.remove(), 150);
        }, duration);
    }

    // Setup modals
    setupModal("createBoardModal", "create-board-btn", "close-create-board-modal");
    setupModal("renameBoardModal", "rename-board-btn", "close-rename-board-modal");
    setupModal("deleteBoardModal", "delete-board-btn", "close-delete-board-modal");

    // Board search functionality
    const searchInput = document.getElementById('board-search');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const boardItems = document.querySelectorAll('.list-group-item');
            
            boardItems.forEach(item => {
                const boardName = item.textContent.toLowerCase();
                if (boardName.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // Board sorting functionality
    function setupBoardSorting() {
        const sortButtons = document.querySelectorAll('[data-sort]');
        sortButtons.forEach(button => {
            button.addEventListener('click', function() {
                const sortBy = this.dataset.sort;
                const boardsList = this.closest('.card-body').querySelector('.list-group');
                const boards = Array.from(boardsList.children);
                
                boards.sort((a, b) => {
                    if (sortBy === 'name') {
                        return a.textContent.localeCompare(b.textContent);
                    } else if (sortBy === 'date') {
                        const dateA = new Date(a.dataset.createdAt);
                        const dateB = new Date(b.dataset.createdAt);
                        return dateB - dateA;
                    }
                });
                
                boards.forEach(board => boardsList.appendChild(board));
            });
        });
    }

    // Board deletion confirmation
    const deleteBoardForm = document.getElementById('delete-board-form');
    if (deleteBoardForm) {
        deleteBoardForm.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this board? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    }

    // Board statistics update
    function updateBoardStatistics() {
        const ownedBoards = document.querySelectorAll('#owned-boards .list-group-item').length;
        const memberBoards = document.querySelectorAll('#member-boards .list-group-item').length;
        
        document.getElementById('owned-boards-count').textContent = ownedBoards;
        document.getElementById('member-boards-count').textContent = memberBoards;
        document.getElementById('total-boards-count').textContent = ownedBoards + memberBoards;
    }

    // Board view toggle (list/grid)
    const viewToggleButtons = document.querySelectorAll('.view-toggle');
    if (viewToggleButtons.length) {
        viewToggleButtons.forEach(button => {
            button.addEventListener('click', function() {
                const view = this.dataset.view;
                const boardsContainer = document.querySelector('.boards-container');
                
                boardsContainer.className = `boards-container ${view}-view`;
                localStorage.setItem('boardsView', view);
                
                viewToggleButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
            });
        });

        // Load saved view preference
        const savedView = localStorage.getItem('boardsView') || 'list';
        document.querySelector(`[data-view="${savedView}"]`).click();
    }

    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });

    // Board access level indicator
    function updateAccessLevelIndicators() {
        const boardItems = document.querySelectorAll('.list-group-item');
        boardItems.forEach(item => {
            const isOwner = item.querySelector('.badge-owner');
            const accessIcon = document.createElement('span');
            accessIcon.className = `access-icon ${isOwner ? 'owner' : 'member'}`;
            accessIcon.setAttribute('data-bs-toggle', 'tooltip');
            accessIcon.setAttribute('data-bs-placement', 'left');
            accessIcon.setAttribute('title', isOwner ? 'Owner' : 'Member');
            item.insertBefore(accessIcon, item.firstChild);
        });
    }

    // Initialize all features
    function initializeFeatures() {
        setupBoardSorting();
        updateBoardStatistics();
        updateAccessLevelIndicators();
    }

    // Call initialization
    initializeFeatures();

    // Handle board creation success/error
    window.addEventListener('load', function() {
        const urlParams = new URLSearchParams(window.location.search);
        const message = urlParams.get('message');
        const error = urlParams.get('error');
        
        if (message) {
            showSuccess(decodeURIComponent(message));
        }
        if (error) {
            showError(decodeURIComponent(error));
        }
    });

    // Success message display
    function showSuccess(message, duration = 3000) {
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success alert-dismissible fade show';
        successDiv.role = 'alert';
        successDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container');
        container.insertBefore(successDiv, container.firstChild);

        setTimeout(() => {
            successDiv.classList.remove('show');
            setTimeout(() => successDiv.remove(), 150);
        }, duration);
    }
});