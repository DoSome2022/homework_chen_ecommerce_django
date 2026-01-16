# products/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Product, ProductCategory, ProductImage, 
    ProductAttribute, ProductAttributeValue, 
    ProductReview, StockChange
)


class ProductImageInline(admin.TabularInline):
    """产品图片内联"""
    model = ProductImage
    extra = 1
    fields = ['image_preview', 'image', 'alt_text', 'is_main', 'display_order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return "无图片"
    
    image_preview.short_description = '预览'


class ProductAttributeValueInline(admin.TabularInline):
    """产品属性值内联"""
    model = ProductAttributeValue
    extra = 1
    fields = ['attribute', 'get_value_display']
    readonly_fields = ['get_value_display']
    
    def get_value_display(self, obj):
        """显示属性值"""
        return obj.value
    
    get_value_display.short_description = '值'


class ProductReviewInline(admin.TabularInline):
    """产品评价内联"""
    model = ProductReview
    extra = 0
    fields = ['customer', 'rating', 'title', 'is_approved']
    readonly_fields = ['customer', 'rating', 'title']
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """产品管理"""
    list_display = [
        'image_preview', 'sku', 'name', 'category', 
        'price', 'stock_quantity', 'is_active', 'is_featured',
        'created_at'
    ]
    list_filter = [
        'is_active', 'is_featured', 'is_bestseller', 'is_new',
        'category', 'created_at'
    ]
    search_fields = ['sku', 'name', 'description']
    list_editable = ['price', 'stock_quantity', 'is_active', 'is_featured']
    list_per_page = 30
    ordering = ['-created_at']
    inlines = [ProductImageInline, ProductAttributeValueInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': (
                'sku', 'name', 'slug', 'category',
                'description', 'short_description',
            )
        }),
        ('价格和库存', {
            'fields': (
                'price', 'cost_price', 'compare_at_price',
                'stock_quantity', 'reorder_level', 'low_stock_threshold',
                'is_track_inventory', 'allow_backorder',
            )
        }),
        ('产品属性', {
            'fields': (
                'weight', 'dimensions', 'color', 'size',
                'material', 'brand',
            )
        }),
        ('状态和标记', {
            'fields': (
                'is_active', 'is_featured', 'is_bestseller', 
                'is_new', 'is_digital', 'tags',
            )
        }),
        ('SEO信息', {
            'fields': (
                'meta_title', 'meta_description', 'meta_keywords',
            )
        }),
        ('统计信息', {
            'fields': (
                'view_count', 'rating', 'review_count',
                'created_at', 'updated_at', 'published_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'published_at']
    
    def image_preview(self, obj):
        """图片预览"""
        main_image = obj.get_main_image()
        if main_image and main_image.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                main_image.image.url
            )
        return "无图片"
    
    image_preview.short_description = '图片'
    
    def stock_status(self, obj):
        """库存状态显示"""
        if obj.is_digital:
            return mark_safe('<span class="badge bg-info">数字产品</span>')
        if not obj.is_track_inventory:
            return mark_safe('<span class="badge bg-secondary">不跟踪库存</span>')
        
        if obj.stock_quantity <= 0:
            return mark_safe('<span class="badge bg-danger">缺货</span>')
        elif obj.stock_quantity <= obj.low_stock_threshold:
            return mark_safe('<span class="badge bg-warning">低库存</span>')
        else:
            return mark_safe('<span class="badge bg-success">有货</span>')
    
    stock_status.short_description = '库存状态'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """产品分类管理"""
    list_display = ['name', 'parent', 'product_count', 'is_active', 'display_order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug', 'description']
    list_editable = ['display_order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description', 'parent', 'image')
        }),
        ('显示设置', {
            'fields': ('display_order', 'is_active')
        }),
        ('SEO信息', {
            'fields': ('meta_title', 'meta_description')
        }),
    )
    
    def product_count(self, obj):
        """产品数量"""
        return obj.products.count()
    
    product_count.short_description = '产品数'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """产品图片管理"""
    list_display = ['product', 'image_preview', 'is_main', 'display_order']
    list_filter = ['product', 'is_main']
    search_fields = ['product__name', 'product__sku']
    list_editable = ['display_order', 'is_main']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "无图片"
    
    image_preview.short_description = '预览'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    """产品属性管理"""
    list_display = ['name', 'code', 'type', 'is_required', 'is_filterable', 'sort_order']
    list_filter = ['type', 'is_required', 'is_filterable']
    search_fields = ['name', 'code']
    list_editable = ['sort_order', 'is_required', 'is_filterable']
    prepopulated_fields = {'code': ('name',)}


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    """产品属性值管理"""
    list_display = ['product', 'attribute', 'value_display']
    list_filter = ['attribute']
    search_fields = ['product__name', 'attribute__name']
    
    def value_display(self, obj):
        return obj.value
    
    value_display.short_description = '值'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'attribute')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """产品评价管理"""
    list_display = ['product', 'customer', 'rating_stars', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'customer__user__username', 'title']
    list_editable = ['is_approved']
    actions = ['approve_reviews', 'reject_reviews']
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return mark_safe(f'<span style="color: gold;">{stars}</span>')
    
    rating_stars.short_description = '评分'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'customer__user')
    
    @admin.action(description='审核通过')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()}条评价已审核通过')
    
    @admin.action(description='拒绝审核')
    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f'{queryset.count()}条评价已被拒绝')


@admin.register(StockChange)
class StockChangeAdmin(admin.ModelAdmin):
    """库存变化记录管理"""
    list_display = ['product', 'quantity', 'action_display', 'current_stock', 'created_at', 'created_by']
    list_filter = ['action', 'created_at']
    search_fields = ['product__name', 'product__sku', 'reference']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def action_display(self, obj):
        action_map = {
            'increase': 'success',
            'decrease': 'danger',
            'adjust': 'warning',
            'reserve': 'info',
            'release': 'secondary',
        }
        color = action_map.get(obj.action, 'secondary')
        
        action_names = {
            'increase': '增加',
            'decrease': '减少',
            'adjust': '调整',
            'reserve': '预留',
            'release': '释放',
        }
        
        name = action_names.get(obj.action, obj.action)
        return mark_safe(f'<span class="badge bg-{color}">{name}</span>')
    
    action_display.short_description = '操作类型'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'created_by')