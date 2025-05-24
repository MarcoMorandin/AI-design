document.addEventListener('DOMContentLoaded', () => {
    const coursesList = document.getElementById('coursesList');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const courseMaterials = document.getElementById('courseMaterials');
    const selectedCourseName = document.getElementById('selectedCourseName');
    const materialsList = document.getElementById('materialsList');
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendMessageButton = document.getElementById('sendMessageButton');
    const logoutButton = document.getElementById('logoutButton');
    const userInitials = document.getElementById('userInitials');
    const userName = document.getElementById('userName');
    const selectedFilesCount = document.getElementById('selectedFilesCount');
    const clearChatButton = document.getElementById('clearChatButton');

    const API_BASE_URL = 'https://ai-design-google-authenticator-595073969012.europe-west8.run.app';
    const LOCAL_API_URL = 'http://localhost:8000'; // For reorganize and chatbot

    let allCoursesData = [];
    let selectedFiles = [];

    // Check authentication status and fetch initial data
    async function initializeDashboard() {
        try {
            // Try to get user profile to check if logged in
            const profileResponse = await fetch(`${API_BASE_URL}/profile`, { credentials: 'include' });

            if (profileResponse.ok) {
                const user = await profileResponse.json();
                updateUserInfo(user);
                fetchCourses();
            } else if (profileResponse.status === 401 || profileResponse.status === 307 || profileResponse.status === 404) {
                // Not authenticated or user not found, redirect to login
                // Check if current page is not already login.html to prevent redirect loop
                if (!window.location.pathname.endsWith('login.html')) {
                    window.location.href = 'login.html';
                }
                return; // Stop further execution if not logged in
            } else {
                console.error('Error fetching profile:', profileResponse.statusText);
                // Handle other errors, maybe show a generic error message
                if (!window.location.pathname.endsWith('login.html')) {
                    window.location.href = 'login.html';
                }
            }
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            if (!window.location.pathname.endsWith('login.html')) {
                window.location.href = 'login.html'; // Redirect on network or other errors
            }
        }
    }

    function updateUserInfo(user) {
        if (user && user.displayName) {
            userName.textContent = user.displayName;
            const initials = user.displayName.split(' ').map(n => n[0]).join('').toUpperCase();
            userInitials.textContent = initials;
        } else {
            userName.textContent = 'User';
            userInitials.textContent = 'U';
        }
    }

    async function fetchCourses() {
        try {
            const response = await fetch(`${API_BASE_URL}/user-courses`, { credentials: 'include' });
            if (!response.ok) {
                if (response.status === 401 || response.status === 307) {
                    window.location.href = 'login.html';
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            allCoursesData = data.courses || [];
            displayCourses(allCoursesData);
        } catch (error) {
            console.error('Error fetching courses:', error);
            coursesList.innerHTML = '<p class="course-item-placeholder">Failed to load courses. Please try again later.</p>';
        }
    }

    function displayCourses(courses) {
        coursesList.innerHTML = ''; // Clear placeholder or old courses
        if (courses.length === 0) {
            coursesList.innerHTML = '<p class="course-item-placeholder">No courses found.</p>';
            return;
        }

        courses.forEach(course => {
            const courseItem = document.createElement('div');
            courseItem.classList.add('course-item');
            courseItem.dataset.courseId = course.course_id;
            courseItem.innerHTML = `
                <div class="course-header">
                    <i class="fas fa-book course-icon"></i>
                    <div class="course-info">
                        <h4>${course.course_name}</h4>
                        <p>${course.course_id.substring(0,6)}...${course.course_id.slice(-4)}</p> <!-- Example: Shortened ID -->
                    </div>
                </div>
                <div class="course-details">
                    <span>${course.document_count} files</span>
                    <span class="course-status">Active</span>
                </div>
                <button class="reorganize-button" data-course-id="${course.course_id}" data-course-name="${course.course_name}">
                    <i class="fas fa-sync-alt"></i> Reorganize
                </button>
            `;
            courseItem.addEventListener('click', (event) => {
                if (event.target.classList.contains('reorganize-button') || event.target.closest('.reorganize-button')) {
                    return; // Handled by separate event listener
                }
                selectCourse(course.course_id);
            });
            coursesList.appendChild(courseItem);
        });

        // Add event listeners for reorganize buttons
        document.querySelectorAll('.reorganize-button').forEach(button => {
            button.addEventListener('click', handleReorganizeClick);
        });
    }

    function selectCourse(courseId) {
        const selectedCourse = allCoursesData.find(c => c.course_id === courseId);
        if (!selectedCourse) return;

        // Highlight selected course in sidebar
        document.querySelectorAll('.course-item').forEach(item => {
            item.classList.remove('selected');
            if (item.dataset.courseId === courseId) {
                item.classList.add('selected');
            }
        });

        welcomeMessage.style.display = 'none';
        courseMaterials.style.display = 'block';
        selectedCourseName.textContent = selectedCourse.course_name;
        displayCourseMaterials(selectedCourse.documents);
        clearChat(); // Clear chat when a new course is selected
        updateChatHeader(selectedCourse.course_name);
    }

    function displayCourseMaterials(documents) {
        materialsList.innerHTML = '';
        selectedFiles = []; // Reset selected files when displaying new materials
        updateSelectedFilesCount();

        if (documents.length === 0) {
            materialsList.innerHTML = '<p>No materials found in this course.</p>';
            return;
        }

        documents.forEach(doc => {
            const materialItem = document.createElement('div');
            materialItem.classList.add('material-item');
            materialItem.innerHTML = `
                <input type="checkbox" id="file-${doc.id}" data-file-id="${doc.id}" data-file-name="${doc.name}">
                <label for="file-${doc.id}" class="file-label">
                    <i class="fas ${getFileIcon(doc.name)} file-icon"></i>
                    <span class="file-name">${doc.name}</span>
                </label>
                <a href="${doc.link}" target="_blank" class="file-link" title="Open file in Drive"><i class="fas fa-external-link-alt"></i></a>
            `;
            materialsList.appendChild(materialItem);

            materialItem.querySelector('input[type="checkbox"]').addEventListener('change', (event) => {
                handleFileSelection(event.target.dataset.fileId, event.target.dataset.fileName, event.target.checked);
            });
        });
    }

    function getFileIcon(fileName) {
        const extension = fileName.split('.').pop().toLowerCase();
        if (['pdf'].includes(extension)) return 'fa-file-pdf';
        if (['doc', 'docx'].includes(extension)) return 'fa-file-word';
        if (['ppt', 'pptx'].includes(extension)) return 'fa-file-powerpoint';
        if (['xls', 'xlsx'].includes(extension)) return 'fa-file-excel';
        if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(extension)) return 'fa-file-image';
        if (['zip', 'rar', 'tar', 'gz'].includes(extension)) return 'fa-file-archive';
        return 'fa-file-alt'; // Default icon
    }

    function handleFileSelection(fileId, fileName, isSelected) {
        if (isSelected) {
            if (!selectedFiles.find(f => f.id === fileId)) {
                selectedFiles.push({ id: fileId, name: fileName });
            }
        } else {
            selectedFiles = selectedFiles.filter(f => f.id !== fileId);
        }
        updateSelectedFilesCount();
    }

    function updateSelectedFilesCount() {
        selectedFilesCount.textContent = `${selectedFiles.length} files selected`;
    }

    async function handleReorganizeClick(event) {
        const courseId = event.target.closest('.reorganize-button').dataset.courseId;
        const courseName = event.target.closest('.reorganize-button').dataset.courseName;
        addMessageToChat(`Reorganizing course: ${courseName}...`, 'bot');
        try {
            const response = await fetch(`${LOCAL_API_URL}/reorganize`, { // Assuming /reorganize is the endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ course_id: courseId, course_name: courseName }), // Send course ID and name
                 credentials: 'include' // If your local API needs cookies/auth from the main app
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error during reorganization.' }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            addMessageToChat(`Reorganization of ${courseName} completed: ${result.message || 'Success!'}`, 'bot');
        } catch (error) {
            console.error('Error reorganizing course:', error);
            addMessageToChat(`Failed to reorganize ${courseName}: ${error.message}`, 'bot');
        }
    }

    function addMessageToChat(text, sender, files = []) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);
        
        let fileInfoHTML = '';
        if (files.length > 0) {
            fileInfoHTML = '<div class="attached-files"><strong>Attached:</strong><ul>';
            files.forEach(file => {
                fileInfoHTML += `<li>${file.name}</li>`;
            });
            fileInfoHTML += '</ul></div>';
        }

        messageDiv.innerHTML = `<p>${text}${fileInfoHTML}</p><span class="timestamp">${new Date().toLocaleTimeString()}</span>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
    }

    async function handleSendMessage() {
        const messageText = chatInput.value.trim();
        if (!messageText && selectedFiles.length === 0) return;

        if (messageText) {
             addMessageToChat(messageText, 'user', selectedFiles);
        }
       
        const currentCourseItem = document.querySelector('.course-item.selected');
        const courseId = currentCourseItem ? currentCourseItem.dataset.courseId : null;

        try {
            // Simulate bot thinking
            setTimeout(async () => {
                const requestBody = {
                    query: messageText,
                    course_id: courseId, // Include course_id if a course is selected
                    selected_files: selectedFiles.map(f => ({id: f.id, name: f.name})) // Send selected file IDs and names
                };

                const response = await fetch(`${LOCAL_API_URL}/chat`, { // Assuming /chat is the endpoint
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody),
                    credentials: 'include' // If your local API needs cookies/auth from the main app
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Chatbot API error.' }));
                    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }
                const result = await response.json();
                addMessageToChat(result.reply || 'Sorry, I could not process your request.', 'bot');
            }, 500); // Simulate delay

        } catch (error) {
            console.error('Error sending message to chatbot:', error);
            addMessageToChat(`Error: ${error.message}`, 'bot');
        }
        
        chatInput.value = ''; // Clear input
        // Uncheck files after sending message
        document.querySelectorAll('.material-item input[type="checkbox"]').forEach(checkbox => checkbox.checked = false);
        selectedFiles = [];
        updateSelectedFilesCount();
        chatInput.style.height = 'auto'; // Reset textarea height
    }

    function clearChat() {
        chatMessages.innerHTML = '';
        addMessageToChat("Hello! I'm your course AI assistant. I can help explain concepts, answer questions about this course, and analyze any materials you select from the left panel. Feel free to ask me anything!", 'bot');
        selectedFiles = [];
        updateSelectedFilesCount();
        document.querySelectorAll('.material-item input[type="checkbox"]').forEach(checkbox => checkbox.checked = false);
    }

    function updateChatHeader(courseName) {
        const chatHeaderP = document.querySelector('.chatbot-header p');
        if (courseName) {
            chatHeaderP.textContent = `Ask questions about ${courseName}`;
        } else {
            chatHeaderP.textContent = 'Ask questions about your selected materials';
        }
    }

    // Event Listeners
    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            try {
                // Optional: Call a backend logout endpoint if it exists and needs to clear server-side session
                // await fetch(`${API_BASE_URL}/logout`, { method: 'GET', credentials: 'include' });
            } catch (error) {
                console.error('Error during server-side logout:', error);
            }
            // Clear client-side session/token indicators if any (e.g., localStorage)
            // For this setup, redirecting to login effectively logs out as session cookies are managed by browser/FastAPI
            window.location.href = `${API_BASE_URL}/logout`; // Redirect to FastAPI logout
        });
    }

    if (sendMessageButton && chatInput) {
        sendMessageButton.addEventListener('click', handleSendMessage);
        chatInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSendMessage();
            }
        });
        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = (chatInput.scrollHeight) + 'px';
        });
    }

    if (clearChatButton) {
        clearChatButton.addEventListener('click', () => {
            const currentCourseItem = document.querySelector('.course-item.selected');
            const courseName = currentCourseItem ? allCoursesData.find(c => c.course_id === currentCourseItem.dataset.courseId)?.course_name : null;
            clearChat();
            updateChatHeader(courseName);
        });
    }

    // Initialize: Only run if on the main dashboard page (index.html)
    if (document.querySelector('.dashboard-container')) {
        initializeDashboard();
    }
});