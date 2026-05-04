from django.urls import path

from . import views


app_name = "communications"

urlpatterns = [
    path("cabinet/", views.cabinet_view, name="cabinet"),
    path("chats/", views.chats_view, name="chats"),
    path("chats/<int:user_id>/", views.chats_view, name="chats_with"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/<int:notification_id>/ack/", views.notification_acknowledge_view, name="notification_ack"),
    path("notifications/<int:notification_id>/question/", views.notification_question_view, name="notification_question"),
    path("tickets/", views.tickets_view, name="tickets"),
    path("support/", views.support_ticket_create_view, name="support_ticket_create"),
    path("support/stats/", views.support_stats_view, name="support_stats"),
    path("tickets/<int:ticket_id>/", views.ticket_detail_view, name="ticket_detail"),
    path("tickets/<int:ticket_id>/messages/", views.ticket_messages_api, name="ticket_messages_api"),
    path("tickets/<int:ticket_id>/important/", views.ticket_toggle_important_view, name="ticket_important"),
    path("tickets/<int:ticket_id>/close/", views.ticket_close_view, name="ticket_close"),
    path("tickets/<int:ticket_id>/reopen/", views.ticket_reopen_view, name="ticket_reopen"),
    path("api/notifications/preview/", views.notifications_preview_api, name="notifications_preview_api"),
    path("api/notifications/send/", views.notifications_send_api, name="notifications_send_api"),
    path("api/chats/state/", views.chats_state_api, name="chats_state_api"),
    path("api/chats/read-all/", views.chats_read_all_api, name="chats_read_all_api"),
    path("api/unread/", views.unread_counts_api, name="unread_counts_api"),
]
