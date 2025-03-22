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
        if (chatContainer.style.display === 'flex') {
            chatContainer.querySelector('.chat-input input').focus();
        }
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
        const loadingId = addMessage('assistant', '<div class="typing-indicator"><span></span><span></span><span></span></div>', true);

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
                        ${product.avg_rating ? `<div class="product-rating">
                            ${generateStarRating(product.avg_rating)}
                            <span class="rating-value">${product.avg_rating}</span>
                        </div>` : ''}
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

    function addMessage(sender, content, isLoading = false) {
        const messageId = 'msg-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.id = messageId;
        messageDiv.innerHTML = content;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
        return messageId;
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function generateStarRating(rating) {
        const fullStars = Math.floor(rating);
        const halfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);

        let starsHtml = '';
        for (let i = 0; i < fullStars; i++) {
            starsHtml += '<i class="fas fa-star"></i>';
        }
        if (halfStar) {
            starsHtml += '<i class="fas fa-star-half-alt"></i>';
        }
        for (let i = 0; i < emptyStars; i++) {
            starsHtml += '<i class="far fa-star"></i>';
        }

        return starsHtml;
    }

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') sendMessage();
    });
});