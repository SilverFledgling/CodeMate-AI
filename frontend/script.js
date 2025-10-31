// ==================== GLOBAL STATE ====================
let currentConversationId = null;
let currentUser = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

// ==================== DOM ELEMENTS ====================
const elements = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    toggleSidebarBtn: document.getElementById('toggle-sidebar'),
    newChatBtn: document.getElementById('new-chat-btn'),
    conversationsList: document.getElementById('conversations-list'),
    logoutBtn: document.getElementById('logout-btn'),
    userNameEl: document.getElementById('user-name'),
    userEmailEl: document.getElementById('user-email'),
    userAvatarEl: document.getElementById('user-avatar'),
    
    // Chat
    chatLog: document.getElementById('chat-log'),
    textInput: document.getElementById('text-input'),
    sendButton: document.getElementById('send-button'),
    micButton: document.getElementById('mic-button'),
    errorBanner: document.getElementById('error-banner'),
    typingIndicator: document.getElementById('ai-typing-indicator'),
    chatTitle: document.getElementById('chat-title'),
};

const API_URL = window.location.origin;

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async () => {
    // Kiểm tra đăng nhập
    const user = await checkAuth();
    if (!user) {
        window.location.href = '/login.html';
        return;
    }
    
    currentUser = user;
    updateUserUI(user);
    
    // Load conversations
    await loadConversations();
    
    // Tạo conversation mới nếu chưa có
    if (!currentConversationId) {
        await createNewConversation();
    }
    
    // Setup event listeners
    setupEventListeners();
});

// ==================== AUTH ====================
async function checkAuth() {
    try {
        const response = await fetch(`${API_URL}/api/auth/me`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const user = await response.json();
            return user;
        }
        return null;
    } catch (error) {
        console.error('Error checking auth:', error);
        return null;
    }
}

async function logout() {
    try {
        await fetch(`${API_URL}/api/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = '/login.html';
    } catch (error) {
        console.error('Logout error:', error);
        showError('Lỗi khi đăng xuất');
    }
}

function updateUserUI(user) {
    elements.userNameEl.textContent = user.full_name || user.email.split('@')[0];
    elements.userEmailEl.textContent = user.email;
    
    if (user.avatar_url) {
        elements.userAvatarEl.innerHTML = `<img src="${user.avatar_url}" alt="Avatar">`;
    } else {
        const initial = user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase();
        elements.userAvatarEl.textContent = initial;
    }
}

// ==================== CONVERSATIONS ====================
async function loadConversations() {
    try {
        const response = await fetch(`${API_URL}/api/conversations`, {
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Không thể tải conversations');
        
        const conversations = await response.json();
        renderConversations(conversations);
        
        // Load conversation đầu tiên nếu có
        if (conversations.length > 0 && !currentConversationId) {
            await loadConversation(conversations[0].id);
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
        showError('Không thể tải lịch sử hội thoại');
    }
}

function renderConversations(conversations) {
    if (conversations.length === 0) {
        elements.conversationsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>Chưa có cuộc hội thoại nào.<br>Nhấn "Trò chuyện mới" để bắt đầu!</p>
            </div>
        `;
        return;
    }
    
    elements.conversationsList.innerHTML = conversations.map(conv => {
        const preview = conv.first_message 
            ? (conv.first_message.length > 60 
                ? conv.first_message.substring(0, 60) + '...' 
                : conv.first_message)
            : 'Không có tin nhắn';
        
        const timeAgo = getTimeAgo(new Date(conv.updated_at));
        const isActive = conv.id === currentConversationId ? 'active' : '';
        
        return `
            <div class="conversation-item ${isActive}" data-id="${conv.id}">
                <div class="conversation-content">
                    <div class="conversation-title">${escapeHtml(conv.title)}</div>
                    <div class="conversation-preview">${escapeHtml(preview)}</div>
                    <div class="conversation-time">${timeAgo}</div>
                </div>
                <div class="conversation-actions">
                    <button class="conversation-action-btn delete" onclick="deleteConversation(${conv.id}, event)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click listeners
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.conversation-actions')) {
                const id = parseInt(item.dataset.id);
                loadConversation(id);
            }
        });
    });
}

async function createNewConversation() {
    try {
        const response = await fetch(`${API_URL}/api/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ title: 'Cuộc hội thoại mới' })
        });
        
        if (!response.ok) throw new Error('Không thể tạo conversation mới');
        
        const data = await response.json();
        currentConversationId = data.conversation_id;
        
        // Reload conversations list
        await loadConversations();
        
        // Clear chat
        elements.chatLog.innerHTML = '';
        elements.chatTitle.textContent = data.title;
        
        showWelcomeScreen();
    } catch (error) {
        console.error('Error creating conversation:', error);
        showError('Không thể tạo cuộc hội thoại mới');
    }
}

async function loadConversation(conversationId) {
    try {
        currentConversationId = conversationId;
        
        // Update active state
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', parseInt(item.dataset.id) === conversationId);
        });
        
        // Load messages
        const response = await fetch(`${API_URL}/api/conversations/${conversationId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Không thể tải messages');
        
        const messages = await response.json();
        
        // Clear chat log
        elements.chatLog.innerHTML = '';
        
        // Render messages
        if (messages.length === 0) {
            showWelcomeScreen();
        } else {
            messages.forEach(msg => {
                addMessageToChatLog(msg.role, msg.content, msg.role === 'assistant');
            });
        }
        
        // Update title
        const convItem = document.querySelector(`.conversation-item[data-id="${conversationId}"]`);
        if (convItem) {
            const title = convItem.querySelector('.conversation-title').textContent;
            elements.chatTitle.textContent = title;
        }
    } catch (error) {
        console.error('Error loading conversation:', error);
        showError('Không thể tải cuộc hội thoại');
    }
}

async function deleteConversation(conversationId, event) {
    event.stopPropagation();
    
    if (!confirm('Bạn có chắc muốn xóa cuộc hội thoại này?')) return;
    
    try {
        const response = await fetch(`${API_URL}/api/conversations/${conversationId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Không thể xóa conversation');
        
        // If deleted current conversation, create new one
        if (conversationId === currentConversationId) {
            await createNewConversation();
        } else {
            await loadConversations();
        }
    } catch (error) {
        console.error('Error deleting conversation:', error);
        showError('Không thể xóa cuộc hội thoại');
    }
}

// ==================== CHAT ====================
async function sendMessage(formData) {
    // Hiển thị tin nhắn user ngay nếu là text
    if (formData.has('text')) {
        const text = formData.get('text');
        addMessageToChatLog('user', text);
        elements.textInput.value = '';
        elements.textInput.style.height = 'auto';
    }
    
    // Hiển thị typing indicator
    showTypingIndicator(true);
    
    // Disable input
    elements.textInput.disabled = true;
    elements.sendButton.disabled = true;
    elements.micButton.disabled = true;
    
    try {
        // Add conversation_id to formData
        formData.append('conversation_id', currentConversationId);
        
        const response = await fetch(`${API_URL}/api/chat`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || 'Có lỗi xảy ra từ server');
        }
        
        const data = await response.json();
        
        // Nếu là audio, hiển thị transcribed text
        if (formData.has('audioFile')) {
            addMessageToChatLog('user', data.user_input);
        }
        
        // Hiển thị AI response
        addMessageToChatLog('assistant', data.ai_response, true);
        
        // Update conversation title nếu là tin nhắn đầu tiên
        await updateConversationTitleIfNeeded(data.user_input);
        
        // Reload conversations để cập nhật preview
        await loadConversations();
        
    } catch (error) {
        console.error('Send message error:', error);
        showError(`Lỗi: ${error.message}`);
        
        // Remove user message if failed
        const lastMessage = elements.chatLog.lastElementChild;
        if (lastMessage && !lastMessage.classList.contains('typing-indicator')) {
            lastMessage.remove();
        }
    } finally {
        showTypingIndicator(false);
        elements.textInput.disabled = false;
        elements.sendButton.disabled = false;
        elements.micButton.disabled = false;
        elements.textInput.focus();
    }
}

async function updateConversationTitleIfNeeded(userInput) {
    try {
        // Chỉ update nếu title vẫn là mặc định
        const convItem = document.querySelector(`.conversation-item[data-id="${currentConversationId}"]`);
        if (convItem) {
            const currentTitle = convItem.querySelector('.conversation-title').textContent;
            if (currentTitle === 'Cuộc hội thoại mới') {
                // Generate title từ user input
                const newTitle = userInput.length > 40 
                    ? userInput.substring(0, 40) + '...' 
                    : userInput;
                
                await fetch(`${API_URL}/api/conversations/${currentConversationId}/title`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ title: newTitle })
                });
                
                elements.chatTitle.textContent = newTitle;
            }
        }
    } catch (error) {
        console.error('Error updating title:', error);
    }
}

function handleSendMessage() {
    const text = elements.textInput.value.trim();
    if (!text) return;
    
    const formData = new FormData();
    formData.append('text', text);
    sendMessage(formData);
}

async function handleVoiceInput() {
    if (isRecording) {
        // Dừng ghi âm
        mediaRecorder.stop();
        isRecording = false;
        elements.micButton.classList.remove('recording');
        elements.micButton.innerHTML = '<i class="fas fa-microphone"></i>';
    } else {
        // Bắt đầu ghi âm
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            audioChunks = [];
            
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const audioFile = new File([audioBlob], "recording.wav", { type: "audio/wav" });
                
                const formData = new FormData();
                formData.append('audioFile', audioFile);
                sendMessage(formData);
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            isRecording = true;
            elements.micButton.classList.add('recording');
            elements.micButton.innerHTML = '<i class="fas fa-stop"></i>';
            
        } catch (error) {
            console.error('Microphone error:', error);
            showError('Không thể truy cập microphone. Vui lòng cấp quyền.');
        }
    }
}

// ==================== UI HELPERS ====================
function addMessageToChatLog(role, content, isMarkdown = false) {
    // Remove welcome screen if exists
    const welcomeScreen = elements.chatLog.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${role}-message`);
    
    const avatar = document.createElement('div');
    avatar.classList.add('message-avatar');
    
    if (role === 'user') {
        if (currentUser && currentUser.avatar_url) {
            avatar.innerHTML = `<img src="${currentUser.avatar_url}" alt="User">`;
        } else {
            const initial = currentUser 
                ? (currentUser.full_name ? currentUser.full_name[0] : currentUser.email[0]) 
                : 'U';
            avatar.textContent = initial.toUpperCase();
        }
    } else {
        avatar.textContent = 'AI';
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    
    if (isMarkdown) {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    elements.chatLog.appendChild(messageDiv);
    
    // Scroll to bottom
    elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
}

function showTypingIndicator(show) {
    elements.typingIndicator.style.display = show ? 'flex' : 'none';
    if (show) {
        elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
    }
}

function showError(message) {
    elements.errorBanner.textContent = message;
    elements.errorBanner.style.display = 'block';
    
    setTimeout(() => {
        elements.errorBanner.style.display = 'none';
    }, 5000);
}

function showWelcomeScreen() {
    elements.chatLog.innerHTML = `
        <div class="welcome-screen">
            <h2>👋 Xin chào! Tôi là CodeMate</h2>
            <p>Tôi có thể giúp bạn với lập trình, công nghệ và nhiều điều khác. Hãy bắt đầu cuộc trò chuyện!</p>
            <div class="welcome-suggestions">
                <div class="suggestion-card" onclick="useSuggestion('Giải thích async/await trong JavaScript')">
                    <i class="fas fa-code"></i>
                    <h3>Học lập trình</h3>
                    <p>Giải thích các khái niệm lập trình</p>
                </div>
                <div class="suggestion-card" onclick="useSuggestion('Viết code Python để đọc file CSV')">
                    <i class="fas fa-terminal"></i>
                    <h3>Viết code</h3>
                    <p>Tạo code mẫu cho dự án</p>
                </div>
                <div class="suggestion-card" onclick="useSuggestion('Debug lỗi này trong code của tôi')">
                    <i class="fas fa-bug"></i>
                    <h3>Debug code</h3>
                    <p>Tìm và sửa lỗi trong code</p>
                </div>
                <div class="suggestion-card" onclick="useSuggestion('Tối ưu hóa thuật toán tìm kiếm')">
                    <i class="fas fa-rocket"></i>
                    <h3>Tối ưu hóa</h3>
                    <p>Cải thiện hiệu suất code</p>
                </div>
            </div>
        </div>
    `;
}

function useSuggestion(text) {
    elements.textInput.value = text;
    elements.textInput.focus();
    handleSendMessage();
}

function toggleSidebar() {
    elements.sidebar.classList.toggle('collapsed');
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    // Sidebar
    elements.toggleSidebarBtn.addEventListener('click', toggleSidebar);
    elements.newChatBtn.addEventListener('click', createNewConversation);
    elements.logoutBtn.addEventListener('click', logout);
    
    // Chat input
    elements.sendButton.addEventListener('click', handleSendMessage);
    elements.micButton.addEventListener('click', handleVoiceInput);
    
    elements.textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Auto-resize textarea
    elements.textInput.addEventListener('input', () => {
        elements.textInput.style.height = 'auto';
        elements.textInput.style.height = `${elements.textInput.scrollHeight}px`;
    });
}

// ==================== UTILITY FUNCTIONS ====================
function getTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Vừa xong';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} phút trước`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} giờ trước`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} ngày trước`;
    
    return date.toLocaleDateString('vi-VN');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make deleteConversation global for onclick
window.deleteConversation = deleteConversation;
window.useSuggestion = useSuggestion;