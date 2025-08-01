document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Enable popovers
    $('[data-toggle="popover"]').popover();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Real-time notification updates
    if (typeof(EventSource) !== "undefined") {
        const source = new EventSource("/notifications/stream");
        
        source.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateNotificationBadge(data.count);
        };
    }
    
    // Chat functionality
    $('.chat-form').on('submit', function(e) {
        e.preventDefault();
        const message = $(this).find('textarea').val().trim();
        
        if (message) {
            // In a real app, this would be an AJAX call
            $(this).find('textarea').val('');
            addMessageToChat(message, true);
        }
    });
    
    // Material download tracking
    $('.download-btn').on('click', function() {
        const materialId = $(this).data('id');
        // Send AJAX request to track download
        $.post('/materials/track', { material_id: materialId });
    });
    
    // Mark notifications as read when clicked
    $('.notification-item').on('click', function() {
        const notificationId = $(this).data('id');
        // Send AJAX request to mark as read
        $.post('/notifications/mark-read', { notification_id: notificationId });
    });
});

function updateNotificationBadge(count) {
    const badge = $('#notificationBadge');
    
    if (count > 0) {
        badge.text(count).show();
    } else {
        badge.hide();
    }
}

function addMessageToChat(message, isSent) {
    const chatMessages = $('.chat-messages');
    const messageClass = isSent ? 'sent' : 'received';
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    const messageHtml = `
        <div class="message ${messageClass} animate-fadeIn">
            ${message}
            <span class="message-time">${timeString}</span>
        </div>
    `;
    
    chatMessages.append(messageHtml);
    chatMessages.scrollTop(chatMessages[0].scrollHeight);
}

// Dark mode toggle
$('#darkModeToggle').on('change', function() {
    $('body').toggleClass('dark-mode');
    localStorage.setItem('darkMode', $(this).is(':checked'));
});

// Check for saved dark mode preference
if (localStorage.getItem('darkMode') === 'true') {
    $('#darkModeToggle').prop('checked', true);
    $('body').addClass('dark-mode');
}