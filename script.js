let currentUser = null;
let currentRoomId = null;
let isBold = false;

function markdownToHtml(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/<br>\s*<br>/g, '<br>');
}

document.getElementById('login-btn').addEventListener('click', async () => {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const response = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    if (data.status === 'success') {
        currentUser = data.username;
        document.getElementById('auth-page').style.display = 'none';
        document.getElementById('app-container').style.display = 'block';
        document.getElementById('room-container').style.display = 'flex';
        loadRooms();
        if (window.joinRoomId) enterRoom(window.joinRoomId, 'Room');
        if (window.viewBlogId) viewBlog(window.viewBlogId);
    } else {
        alert(data.message);
    }
});

document.getElementById('signup-link').addEventListener('click', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const response = await fetch('/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    alert(data.message);
});

document.getElementById('logout-btn').addEventListener('click', () => {
    currentUser = null;
    currentRoomId = null;
    document.getElementById('app-container').style.display = 'none';
    document.getElementById('auth-page').style.display = 'flex';
});

async function loadRooms() {
    const response = await fetch('/rooms');
    const data = await response.json();
    if (data.status !== 'success') {
        alert(data.message);
        return;
    }
    const roomList = document.getElementById('room-list');
    roomList.innerHTML = '';
    data.rooms.forEach(room => {
        const div = document.createElement('div');
        div.classList.add('room-item');
        div.innerHTML = `${room.name} <button class="delete-btn">Delete</button>`;
        div.querySelector('.delete-btn').addEventListener('click', async (e) => {
            e.stopPropagation();
            const response = await fetch(`/rooms/${room.id}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.status === 'success') loadRooms();
            else alert(data.message);
        });
        div.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON') enterRoom(room.id, room.name);
        });
        roomList.appendChild(div);
    });
}

document.getElementById('create-room-btn').addEventListener('click', async () => {
    const roomName = document.getElementById('room-name').value.trim();
    if (roomName) {
        const response = await fetch('/rooms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_name: roomName })
        });
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('room-name').value = '';
            loadRooms();
        } else {
            alert(data.message);
        }
    }
});

async function enterRoom(roomId, roomName) {
    currentRoomId = roomId;
    document.getElementById('room-container').style.display = 'none';
    document.getElementById('chat-container').style.display = 'flex';
    document.getElementById('chat-room-name').textContent = roomName;
    document.getElementById('invite-link').value = `${window.location.origin}/join/${roomId}`;
    loadMessages();
    clearInterval(window.messageInterval);
    window.messageInterval = setInterval(loadMessages, 1000);
}

async function loadMessages() {
    const response = await fetch(`/messages/${currentRoomId}`);
    const data = await response.json();
    if (data.status !== 'success') {
        alert(data.message);
        document.getElementById('chat-container').style.display = 'none';
        document.getElementById('room-container').style.display = 'flex';
        loadRooms();
        return;
    }
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = '';
    data.messages.forEach(msg => {
        const p = document.createElement('p');
        p.classList.add(msg.sender === currentUser ? 'me' : 'friend');
        p.textContent = `${msg.sender}: ${msg.content} (${new Date(msg.timestamp).toLocaleTimeString()})`;
        if (msg.file_path) {
            const link = document.createElement('a');
            link.href = `/uploads/${msg.file_path.split('/').pop()}`;
            link.textContent = ' [File]';
            link.target = '_blank';
            p.appendChild(link);
        }
        chatMessages.appendChild(p);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

document.getElementById('send-btn').addEventListener('click', async () => {
    const message = document.getElementById('message-input').value.trim();
    const fileInput = document.getElementById('message-file');
    if (message || fileInput.files.length > 0) {
        const formData = new FormData();
        formData.append('room_id', currentRoomId);
        formData.append('content', message);
        if (fileInput.files.length > 0) formData.append('file', fileInput.files[0]);
        const response = await fetch('/messages', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('message-input').value = '';
            fileInput.value = '';
            loadMessages();
        } else {
            alert(data.message || 'Error posting message');
        }
    }
});

document.getElementById('copy-invite-btn').addEventListener('click', () => {
    const inviteLink = document.getElementById('invite-link');
    inviteLink.select();
    document.execCommand('copy');
    alert('Invite link copied!');
});

document.getElementById('back-to-rooms-btn').addEventListener('click', () => {
    clearInterval(window.messageInterval);
    document.getElementById('chat-container').style.display = 'none';
    document.getElementById('room-container').style.display = 'flex';
    loadRooms();
});

document.getElementById('blogs-btn').addEventListener('click', () => {
    document.getElementById('room-container').style.display = 'none';
    document.getElementById('blog-container').style.display = 'flex';
    loadBlogs();
});

document.getElementById('back-to-rooms-btn-blog').addEventListener('click', () => {
    document.getElementById('blog-container').style.display = 'none';
    document.getElementById('room-container').style.display = 'flex';
    loadRooms();
});

document.getElementById('bold-toggle-btn').addEventListener('click', () => {
    isBold = !isBold;
    const blogInput = document.getElementById('blog-input');
    if (isBold) {
        blogInput.value += '**';
        document.getElementById('bold-toggle-btn').style.background = '#6b48ff';
    } else {
        blogInput.value += '**';
        document.getElementById('bold-toggle-btn').style.background = '#ff6b6b';
    }
    blogInput.focus();
});

document.getElementById('post-blog-btn').addEventListener('click', async () => {
    const content = document.getElementById('blog-input').value.trim();
    const fileInput = document.getElementById('blog-file');
    console.log('Posting blog with content:', content, 'and file:', fileInput.files[0]); // Debug
    if (content || fileInput.files.length > 0) {
        const formData = new FormData();
        formData.append('content', content);
        if (fileInput.files.length > 0) formData.append('file', fileInput.files[0]);
        try {
            const response = await fetch('/blogs', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            console.log('Blog post response:', data); // Debug
            if (data.status === 'success') {
                document.getElementById('blog-input').value = '';
                fileInput.value = '';
                isBold = false;
                document.getElementById('bold-toggle-btn').style.background = '#ff6b6b';
                loadBlogs();
            } else {
                alert(data.message || 'Error posting blog');
            }
        } catch (error) {
            console.error('Fetch error:', error); // Debug
            alert('Network error while posting blog');
        }
    } else {
        alert('Please enter content or upload a file');
    }
});

async function loadBlogs() {
    const response = await fetch('/blogs');
    const data = await response.json();
    if (data.status !== 'success') {
        alert(data.message);
        return;
    }
    const blogPosts = document.getElementById('blog-posts');
    blogPosts.innerHTML = '';
    data.blogs.forEach(blog => {
        const div = document.createElement('div');
        div.classList.add('blog-post');
        div.innerHTML = `
            <p>${markdownToHtml(blog.content)}</p>
            <small>By ${blog.author} on ${new Date(blog.timestamp).toLocaleString()}</small>
            ${blog.file_path ? `<a href="/uploads/${blog.file_path.split('/').pop()}" target="_blank">[File]</a>` : ''}
            ${blog.author === currentUser ? '<button class="delete-btn">Delete</button>' : ''}
        `;
        if (blog.author === currentUser) {
            div.querySelector('.delete-btn').addEventListener('click', async () => {
                const response = await fetch(`/blogs/${blog.id}`, { method: 'DELETE' });
                const data = await response.json();
                if (data.status === 'success') loadBlogs();
            });
        }
        div.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'A') viewBlog(blog.id);
        });
        blogPosts.appendChild(div);
    });
}

async function viewBlog(blogId) {
    const response = await fetch(`/blogs/${blogId}`);
    const data = await response.json();
    if (data.status !== 'success') {
        alert(data.message);
        return;
    }
    document.getElementById('blog-container').style.display = 'none';
    document.getElementById('blog-view').style.display = 'flex';
    document.getElementById('blog-content').innerHTML = `
        <p>${markdownToHtml(data.blog.content)}</p>
        <small>By ${data.blog.author} on ${new Date(data.blog.timestamp).toLocaleString()}</small>
        ${data.blog.file_path ? `<a href="/uploads/${data.blog.file_path.split('/').pop()}" target="_blank">[File]</a>` : ''}
    `;
    document.getElementById('blog-share-link').value = `${window.location.origin}/blog/${blogId}`;
}

document.getElementById('copy-blog-link-btn').addEventListener('click', () => {
    const shareLink = document.getElementById('blog-share-link');
    shareLink.select();
    document.execCommand('copy');
    alert('Blog link copied!');
});

document.getElementById('back-to-blogs-btn').addEventListener('click', () => {
    document.getElementById('blog-view').style.display = 'none';
    document.getElementById('blog-container').style.display = 'flex';
    loadBlogs();
});
