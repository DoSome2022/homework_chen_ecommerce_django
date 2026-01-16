# products/apps.py
from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # 改為這一行（推薦）
    name = 'products'
    verbose_name = '产品管理'
    
    # def ready(self):
    #     """应用就绪时执行"""
    #     import products.signals  # 如果有信号处理