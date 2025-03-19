document.addEventListener('DOMContentLoaded', function () {
    const chatIcon = document.querySelector('.chatbox-icon');
    const chatContainer = document.createElement('div');
    chatContainer.className = 'chat-container';
    chatContainer.innerHTML = `
        <div class="chat-header">
            <h3>Amazon Product Assistant</h3>
            <button class="close-chat">×</button>
        </div>
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input">
            <input type="text" placeholder="Ask about products...">
            <button>Send</button>
        </div>
    `;
    document.body.appendChild(chatContainer);
    chatContainer.style.display = 'none';

    // Toggle chat
    chatIcon.addEventListener('click', function () {
        chatContainer.style.display = chatContainer.style.display === 'none' ? 'flex' : 'none';
    });

    // Close chat
    chatContainer.querySelector('.close-chat').addEventListener('click', function () {
        chatContainer.style.display = 'none';
    });

    // Send message
    const sendButton = chatContainer.querySelector('.chat-input button');
    const inputField = chatContainer.querySelector('.chat-input input');
    const messagesContainer = chatContainer.querySelector('.chat-messages');

    function sendMessage() {
        const message = inputField.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage('user', message);
        inputField.value = '';

        // Show loading indicator
        const loadingId = addMessage('assistant', '...', true);

        // Send to backend
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: message }),
        })
            .then(response => response.json())
            .then(data => {
                // Remove loading indicator
                document.getElementById(loadingId).remove();

                // Add assistant response
                addMessage('assistant', data.response);

                // Add product suggestions if any
                if (data.products && data.products.length > 0) {
                    const productsHtml = data.products.map(product =>
                        `<div class="product-suggestion">
                        <a href="/product/${product.asin}">${product.title}</a>
                    </div>`
                    ).join('');

                    const productsContainer = document.createElement('div');
                    productsContainer.className = 'products-container';
                    productsContainer.innerHTML = `
                    <h4>Suggested Products:</h4>
                    ${productsHtml}
                `;
                    messagesContainer.appendChild(productsContainer);
                    scrollToBottom();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Remove loading indicator
                document.getElementById(loadingId).remove();
                addMessage('assistant', 'Sorry, there was an error processing your request.');
            });
    }

    function addMessage(sender, text, isLoading = false) {
        const messageId = 'msg-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.id = messageId;
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
        return messageId;
    }

    function scrollToBottom() {
        // Ensure chat always scrolls to the bottom when new messages appear
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') sendMessage();
    });
});