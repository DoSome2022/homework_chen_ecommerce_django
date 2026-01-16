from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # 改為這一行（推薦）
    name = 'accounts'
    verbose_name = '账户管理'