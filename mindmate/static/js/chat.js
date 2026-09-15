const chatLog = document.getElementById('chatLog');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');

function scrollToBottom() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function appendMessage(text, sender, isCrisis = false) {
  const div = document.createElement('div');
  div.classList.add('msg', sender === 'user' ? 'msg-user' : 'msg-bot');
  if (isCrisis) div.classList.add('crisis');
  div.textContent = text;
  chatLog.appendChild(div);
  scrollToBottom();
}

function appendTip(text) {
  const div = document.createElement('div');
  div.classList.add('msg-tip');
  div.textContent = '💡 ' + text;
  chatLog.appendChild(div);
  scrollToBottom();
}

function appendCrisisResources(resources) {
  const box = document.createElement('div');
  box.classList.add('crisis-box');
  let html = '<h4>You deserve support right now — please reach out:</h4><ul>';
  resources.india.forEach(r => {
    html += `<li><strong>${r.name}</strong>: ${r.phone}</li>`;
  });
  resources.international.forEach(r => {
    html += `<li><strong>${r.name}</strong>: ${r.phone}</li>`;
  });
  html += '</ul><p style="margin:0.5rem 0 0;">If you feel you might act on these thoughts, please contact local emergency services or go to the nearest hospital right away.</p>';
  box.innerHTML = html;
  chatLog.appendChild(box);
  scrollToBottom();
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage(text, 'user');
  chatInput.value = '';
  chatInput.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();

    if (!res.ok) {
      appendMessage("Sorry, something went wrong. Please try again.", 'bot');
    } else {
      appendMessage(data.reply, 'bot', data.is_crisis);
      if (data.tip) appendTip(data.tip);
      if (data.is_crisis && data.crisis_resources) appendCrisisResources(data.crisis_resources);
    }
  } catch (err) {
    appendMessage("Network error — is the server running?", 'bot');
  } finally {
    chatInput.disabled = false;
    chatInput.focus();
  }
});

scrollToBottom();
