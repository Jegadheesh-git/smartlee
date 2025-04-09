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
    path('daily-revision/create/', views.create_daily_revision, name='create_daily_revision'),
    path('daily-revision/revise/<int:id>/', views.mark_as_revised, name='mark_as_revised'),
    path('delete/problem/<int:pk>/', views.delete_problem, name='delete_problem'),
    path('delete/dailyrevision/<int:pk>/', views.delete_dailyrevision, name='delete_dailyrevision'),
    path('edit/dailyrevision/<int:pk>/', views.edit_dailyrevision, name='edit_dailyrevision'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    
]
