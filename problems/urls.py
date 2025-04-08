from django.urls import path
from . import views

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('add/', views.add_problem, name='add_problem'),
    path('edit/<int:pk>/', views.edit_problem, name='edit_problem'),
     path('revision/', views.revision_queue, name='revision_queue'),
    path('revision/mark/<int:pk>/', views.mark_revision_complete, name='mark_revision_complete'),
    path('toggle/<int:pk>/', views.toggle_complete, name='toggle_complete'),
    path('skip-revision/', views.skip_revision, name='skip_revision'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    
]
