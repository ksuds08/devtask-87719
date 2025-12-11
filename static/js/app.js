const API_BASE = '';

function getToken() {
  return localStorage.getItem('access_token');
}

function setToken(token) {
  localStorage.setItem('access_token', token);
}

function clearToken() {
  localStorage.removeItem('access_token');
}

async function apiRequest(path, options = {}) {
  const headers = options.headers || {};
  if (getToken()) {
    headers['Authorization'] = `Bearer ${getToken()}`;
  }
  headers['Content-Type'] = 'application/json';

  const res = await fetch(API_BASE + path, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

// Auth flows
const loginForm = document.getElementById('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    try {
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      setToken(data.access_token);
      window.location.href = '/dashboard';
    } catch (err) {
      alert('Login failed');
      console.error(err);
    }
  });
}

const signupForm = document.getElementById('signup-form');
if (signupForm) {
  signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    try {
      await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      // auto-login after signup
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      setToken(data.access_token);
      window.location.href = '/dashboard';
    } catch (err) {
      alert('Signup failed');
      console.error(err);
    }
  });
}

// Dashboard logic
const tasksTableBody = document.querySelector('#tasks-table tbody');
const newTaskForm = document.getElementById('new-task-form');
const logoutBtn = document.getElementById('logout-btn');

if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    clearToken();
    window.location.href = '/';
  });
}

async function loadTasks() {
  if (!tasksTableBody) return;
  try {
    const tasks = await apiRequest('/tasks');
    tasksTableBody.innerHTML = '';
    tasks.forEach((task) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${task.title}</td>
        <td>${task.status}</td>
        <td>${task.time_logged}</td>
        <td>
          <button data-id="${task.id}" class="delete-btn">Delete</button>
        </td>
      `;
      tasksTableBody.appendChild(tr);
    });

    document.querySelectorAll('.delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('Delete this task?')) return;
        try {
          await apiRequest(`/tasks/${id}`, { method: 'DELETE' });
          loadTasks();
        } catch (err) {
          alert('Failed to delete task');
        }
      });
    });
  } catch (err) {
    console.error(err);
    if (err.message.includes('401')) {
      window.location.href = '/login';
    }
  }
}

if (newTaskForm) {
  newTaskForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('task-title').value;
    const status = document.getElementById('task-status').value;
    const time_logged = parseFloat(document.getElementById('task-time').value || '0');
    try {
      await apiRequest('/tasks', {
        method: 'POST',
        body: JSON.stringify({ title, status, time_logged })
      });
      newTaskForm.reset();
      loadTasks();
    } catch (err) {
      alert('Failed to create task');
      console.error(err);
    }
  });

  // initial load
  loadTasks();
}
