from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # 公共页面
    path('', views.home_view, name='home'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # 客户相关
    path('customer/dashboard/', views.CustomerDashboardView.as_view(), name='customer_dashboard'),
    path('customer/profile/', views.CustomerProfileView.as_view(), name='customer_profile'),
    path('customer/change-password/', views.change_password_view, name='change_password'),
    
    # 员工相关
    path('staff/dashboard/', views.StaffDashboardView.as_view(), name='staff_dashboard'),
    path('staff/profile/', views.StaffProfileView.as_view(), name='staff_profile'),
    
    # 管理员功能
    path('admin/users/', views.UserListView.as_view(), name='user_list'),
    path('admin/users/<uuid:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('admin/users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('admin/users/<uuid:user_id>/create-staff/', views.create_staff, name='create_staff'),
    
    # 客户等级管理
    path('admin/customer-levels/', views.CustomerLevelListView.as_view(), name='customer_level_list'),
    path('admin/customer-levels/create/', views.CustomerLevelCreateView.as_view(), name='customer_level_create'),
    path('admin/customer-levels/<uuid:pk>/edit/', views.CustomerLevelUpdateView.as_view(), name='customer_level_edit'),
]