document.addEventListener('DOMContentLoaded', function () {
    const chatIcon = document.querySelector('.chatbox-icon');
    const chatContainer = document.createElement('div');
    chatContainer.className = 'chat-container';
    chatContainer.innerHTML = `
        <div class="chat-header">
            <div class="chat-header-title">
                <div class="bot-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <h3>CheeseCake Assistant</h3>
            </div>
            <div class="chat-header-actions">
                <button class="minimize-chat"><i class="fas fa-minus"></i></button>
                <button class="close-chat"><i class="fas fa-times"></i></button>
            </div>
        </div>
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input">
            <div class="input-wrapper">
                <input type="text" placeholder="Type your message...">
                <button class="send-button">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
            <div class="chat-footer">
                <span>Powered by Amazon SNAP - Graph Database</span>
            </div>
        </div>
    `;
    document.body.appendChild(chatContainer);
    chatContainer.style.display = 'none';

    const closeChat = chatContainer.querySelector('.close-chat');
    const minimizeChat = chatContainer.querySelector('.minimize-chat');
    const chatMessages = chatContainer.querySelector('.chat-messages');
    const chatInput = chatContainer.querySelector('.chat-input input');
    const chatSendButton = chatContainer.querySelector('.send-button');

    chatIcon.addEventListener('click', () => {
        chatContainer.style.display = 'flex';
        chatIcon.style.display = 'none';
        chatContainer.classList.add('chat-enter');
        setTimeout(() => chatContainer.classList.remove('chat-enter'), 500);
        chatInput.focus();
    });

    closeChat.addEventListener('click', () => {
        chatContainer.classList.add('chat-exit');
        setTimeout(() => {
            chatContainer.style.display = 'none';
            chatIcon.style.display = 'flex';
            chatContainer.classList.remove('chat-exit');
        }, 500);
    });

    minimizeChat.addEventListener('click', () => {
        chatContainer.classList.add('chat-minimize');
        setTimeout(() => {
            chatContainer.style.display = 'none';
            chatIcon.style.display = 'flex';
            chatContainer.classList.remove('chat-minimize');
        }, 500);
    });

    function addMessage(sender, content, isLoading = false) {
        const messageId = 'msg-' + Date.now();
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}-message`;
        messageElement.id = messageId;

        if (sender === 'assistant') {
            messageElement.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-bubble">
                    ${content}
                </div>
            `;
        } else {
            messageElement.innerHTML = `
                <div class="message-bubble">
                    ${content}
                </div>
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
            `;
        }

        chatMessages.appendChild(messageElement);

        // Add animation class
        setTimeout(() => {
            messageElement.classList.add('message-appear');
        }, 10);

        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageId;
    }

    function handleUserInput() {
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage('user', `<div class='message-content'>${message}</div>`);
        chatInput.value = '';

        const loadingId = addMessage('assistant', `<div class="typing-indicator"><span></span><span></span><span></span></div>`, true);

        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: message }),
        })
            .then(response => response.json())
            .then(data => {
                document.getElementById(loadingId).remove();
                addMessage('assistant', `<div class='message-content'>${data.response}</div>`);

                if (data.products && data.products.length > 0) {
                    const productsHtml = data.products.map(product =>
                        `<div class="product-suggestion">
                            <a href="/product/${product.asin}">
                                <div class="product-title">${product.title}</div>
                                ${product.avg_rating ? `<div class="product-rating">
                                    ${generateStarRating(product.avg_rating)}
                                    <span class="rating-value">${product.avg_rating}</span>
                                </div>` : ''}
                            </a>
                        </div>`
                    ).join('');

                    const productsMessage = document.createElement('div');
                    productsMessage.className = 'message assistant-message';
                    productsMessage.innerHTML = `
                        <div class="message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-bubble">
                            <div class="products-container">
                                <h4>Suggested Products:</h4>
                                <div class="products-carousel">
                                    ${productsHtml}
                                </div>
                            </div>
                        </div>
                    `;

                    chatMessages.appendChild(productsMessage);

                    // Add animation class
                    setTimeout(() => {
                        productsMessage.classList.add('message-appear');
                    }, 10);

                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById(loadingId).remove();
                addMessage('assistant', '<div class="message-content">Sorry, there was an error processing your request.</div>');
            });
    }

    function generateStarRating(rating) {
        const fullStars = Math.floor(rating);
        const halfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);
        let starsHtml = '';
        for (let i = 0; i < fullStars; i++) starsHtml += '<i class="fas fa-star"></i>';
        if (halfStar) starsHtml += '<i class="fas fa-star-half-alt"></i>';
        for (let i = 0; i < emptyStars; i++) starsHtml += '<i class="far fa-star"></i>';
        return starsHtml;
    }

    chatSendButton.addEventListener('click', handleUserInput);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleUserInput();
    });

    // Add a slight delay to the welcome message for a better effect
    setTimeout(() => {
        addMessage('assistant', "<div class='message-content'>Hello! I'm CheeseCake Assistant. How can I help you today?</div>");
    }, 500);
});