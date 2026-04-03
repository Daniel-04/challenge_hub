from django.urls import path
from . import views

urlpatterns = [
    path('', views.challenge_list, name='challenge_list'),
    path('<int:pk>/', views.challenge_detail, name='challenge_detail'),
    path('<int:pk>/submit/', views.challenge_submit, name='challenge_submit'),
    path('<int:pk>/rate/', views.challenge_rate, name='challenge_rate'),
    path('<int:pk>/difficulty/', views.challenge_difficulty, name='challenge_difficulty'),
    path('<int:pk>/comment/', views.challenge_comment, name='challenge_comment'),
    path('<int:pk>/mark_completed/', views.challenge_mark_completed, name='challenge_mark_completed'),
    path('testcase/<int:tc_id>/download/<str:which>/', views.testcase_download, name='testcase_download'),
    path('upload/', views.challenge_upload, name='challenge_upload'),
    
    path('session/pow/challenge/', views.session_pow_challenge, name='session_pow_challenge'),
    path('session/pow/solve/', views.session_pow_solve, name='session_pow_solve'),
    path('session/export/', views.session_export, name='session_export'),
    path('session/import/', views.session_import, name='session_import'),
]
