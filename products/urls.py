# products/urls.py
from django.urls import path, include
from . import views

app_name = 'products'

urlpatterns = [
    # 前台页面
    path('', views.ProductListView.as_view(), name='product_list'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # 搜索和API
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),
    path('api/product/<uuid:pk>/', views.product_api, name='product_api'),
    
    # 后台管理
    path('admin/', include([
        path('products/', views.AdminProductListView.as_view(), name='admin_product_list'),
        path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
        path('products/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
        path('products/<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
        path('products/<uuid:pk>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
        path('products/<uuid:pk>/images/', views.update_product_images, name='update_product_images'),
        
        path('categories/', views.CategoryListView.as_view(), name='admin_category_list'),
        path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
        path('categories/<uuid:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
        path('categories/<uuid:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
        
        path('reviews/', views.product_review_list, name='review_list'),
        path('reviews/<uuid:pk>/approve/', views.approve_review, name='approve_review'),
        path('reviews/<uuid:pk>/delete/', views.delete_review, name='delete_review'),
        
        # AJAX 操作
        path('image/<uuid:pk>/delete/', views.delete_product_image, name='delete_product_image'),
        path('image/<uuid:pk>/set-main/', views.set_main_image, name='set_main_image'),
    ])),
]