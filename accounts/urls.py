from django.urls import path
from .views import CustomLoginView
from django.contrib.auth import views as auth_views # Para otras vistas de auth


urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    #path('login/', CustomLoginView.as_view(), name='login_old'),
    # Puedes añadir aquí otras URLs de la app 'accounts' si las necesitas,
    # o importar el resto de django.contrib.auth.urls en core/urls.py
    # por ejemplo, para logout, cambio de contraseña, etc.
    # path('logout/', auth_views.LogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
    # path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), name='password_change'),
    # path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    # path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    # path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    # path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    # path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]