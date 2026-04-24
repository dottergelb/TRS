                  
from django.urls import path
from .views import (
    login_view,
    register_view,
    logout_view,
    user_list_view,
    user_edit_view,
    user_delete_view,
)

                                                             
app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
                                        
    path('users/', user_list_view, name='user_list'),
    path('users/<int:user_id>/edit/', user_edit_view, name='user_edit'),
    path('users/<int:user_id>/delete/', user_delete_view, name='user_delete'),
]
