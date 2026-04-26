from django.contrib import admin

from .models import (
    ChatMessage,
    NotificationReplacementItem,
    NotificationStatus,
    SystemNotification,
    Ticket,
    TicketMessage,
    TicketParticipant,
)


admin.site.register(ChatMessage)
admin.site.register(SystemNotification)
admin.site.register(NotificationReplacementItem)
admin.site.register(NotificationStatus)
admin.site.register(Ticket)
admin.site.register(TicketMessage)
admin.site.register(TicketParticipant)

