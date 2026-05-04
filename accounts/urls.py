                  
from django.urls import path
from .views import (
    entry_view,
    login_view,
    project_hub_view,
    project_users_view,
    project_user_delete_view,
    project_select_school_view,
    register_view,
    logout_view,
    school_register_request_view,
    school_request_approve_view,
    school_request_review_view,
    school_request_reject_view,
    user_list_view,
    user_edit_view,
    user_delete_view,
    export_teacher_credentials_view,
    import_teachers_from_file_view,
)

                                                             
app_name = 'accounts'

urlpatterns = [
    path('', entry_view, name='entry'),
    path('login/', login_view, name='login'),
    path('project/', project_hub_view, name='project_hub'),
    path('project/users/', project_users_view, name='project_users'),
    path('project/users/<int:user_id>/delete/', project_user_delete_view, name='project_user_delete'),
    path('project/schools/<int:school_id>/select/', project_select_school_view, name='project_select_school'),
    path('project/schools/<int:school_id>/review/', school_request_review_view, name='school_request_review'),
    path('project/schools/<int:school_id>/approve/', school_request_approve_view, name='school_request_approve'),
    path('project/schools/<int:school_id>/reject/', school_request_reject_view, name='school_request_reject'),
    path('schools/register/', school_register_request_view, name='school_register_request'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
                                        
    path('users/', user_list_view, name='user_list'),
    path('users/export-teacher-credentials/', export_teacher_credentials_view, name='export_teacher_credentials'),
    path('users/import-teachers/', import_teachers_from_file_view, name='import_teachers_from_file'),
    path('users/<int:user_id>/edit/', user_edit_view, name='user_edit'),
    path('users/<int:user_id>/delete/', user_delete_view, name='user_delete'),
]
