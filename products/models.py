#products/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class ProductCategory(models.Model):
    """产品分类"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('分类名称', max_length=100)
    slug = models.SlugField('URL标识', max_length=100, unique=True)
    description = models.TextField('描述', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='children')
    image = models.ImageField('分类图片', upload_to='category_images/', null=True, blank=True)
    is_active = models.BooleanField('是否激活', default=True)
    display_order = models.IntegerField('显示顺序', default=0)

    # SEO 信息
    meta_title = models.CharField('Meta标题', max_length=200, blank=True)
    meta_description = models.TextField('Meta描述', blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '产品分类'
        verbose_name_plural = '产品分类'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def product_count(self):
        """获取分类下的产品数量（仅统计激活产品）"""
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    """产品"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '上架'),
        ('inactive', '下架'),
        ('archived', '归档'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField('SKU编码', max_length=50, unique=True, db_index=True)
    name = models.CharField('产品名称', max_length=200)
    slug = models.SlugField('URL标识', max_length=200, unique=True)
    description = models.TextField('详细描述', blank=True)
    short_description = models.TextField('简短描述', max_length=500, blank=True)

    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='products')

    # 价格信息
    price = models.DecimalField('销售价格', max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(0)])
    cost_price = models.DecimalField('成本价格', max_digits=10, decimal_places=2,
                                     validators=[MinValueValidator(0)], null=True, blank=True)
    compare_at_price = models.DecimalField('比较价格', max_digits=10, decimal_places=2,
                                           null=True, blank=True, validators=[MinValueValidator(0)])

    # 库存信息
    is_track_inventory = models.BooleanField('跟踪库存', default=True)
    stock_quantity = models.IntegerField('库存数量', default=0)
    reorder_level = models.IntegerField('补货点', default=10)
    low_stock_threshold = models.IntegerField('低库存阈值', default=5)
    allow_backorder = models.BooleanField('允许缺货订购', default=False)

    # 产品属性（物理）
    weight = models.DecimalField('重量(kg)', max_digits=8, decimal_places=3,
                                 null=True, blank=True, validators=[MinValueValidator(0)])
    dimensions = models.CharField('尺寸(LxWxH cm)', max_length=100, blank=True)
    color = models.CharField('颜色', max_length=50, blank=True)
    size = models.CharField('尺寸', max_length=50, blank=True)
    material = models.CharField('材质', max_length=100, blank=True)
    brand = models.CharField('品牌', max_length=100, blank=True)

    # 状态与标记
    is_active = models.BooleanField('是否上架', default=True)
    is_featured = models.BooleanField('推荐产品', default=False)
    is_bestseller = models.BooleanField('热销产品', default=False)
    is_new = models.BooleanField('新品', default=False)
    is_digital = models.BooleanField('数字产品', default=False)
    tags = models.CharField('标签', max_length=500, blank=True)

    # SEO 信息
    meta_title = models.CharField('Meta标题', max_length=200, blank=True)
    meta_description = models.TextField('Meta描述', blank=True)
    meta_keywords = models.CharField('Meta关键词', max_length=255, blank=True)

    # 统计信息
    view_count = models.PositiveIntegerField('浏览数', default=0)
    rating = models.DecimalField('平均评分', max_digits=3, decimal_places=2, default=0.00)
    review_count = models.PositiveIntegerField('评价数', default=0)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_products')

    class Meta:
        verbose_name = '产品'
        verbose_name_plural = '产品'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['is_active']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_main_image(self):
        """返回主图（用于 admin 预览）"""
        return self.images.filter(is_main=True).first()


class ProductImage(models.Model):
    """产品图片"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('图片', upload_to='products/images/')
    alt_text = models.CharField('替代文本', max_length=255, blank=True)
    is_main = models.BooleanField('是否主图', default=False)
    display_order = models.PositiveIntegerField('显示顺序', default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name = '产品图片'
        verbose_name_plural = '产品图片'

    def __str__(self):
        return f"图片 - {self.product.name}"


class ProductAttribute(models.Model):
    """产品属性（如颜色、尺寸等）"""
    name = models.CharField('属性名称', max_length=100)
    code = models.SlugField('属性代码', max_length=100, unique=True)
    type = models.CharField('类型', max_length=20,
                            choices=[('text', '文本'), ('integer', '整数'), ('boolean', '布尔')])
    is_required = models.BooleanField('必填', default=False)
    is_filterable = models.BooleanField('可筛选', default=False)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        ordering = ['sort_order']
        verbose_name = '产品属性'
        verbose_name_plural = '产品属性'

    def __str__(self):
        return self.name


class ProductAttributeValue(models.Model):
    """产品属性值"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.CharField('值', max_length=500)

    class Meta:
        unique_together = ['product', 'attribute']
        verbose_name = '产品属性值'
        verbose_name_plural = '产品属性值'

    def __str__(self):
        return f"{self.product.name} - {self.attribute.name}: {self.value}"

    @property
    def get_value_display(self):
        return self.value


class ProductReview(models.Model):
    """产品评价"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE,
                                 related_name='product_reviews')
    rating = models.PositiveIntegerField('评分', validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField('标题', max_length=200, blank=True)
    comment = models.TextField('内容', blank=True)
    is_approved = models.BooleanField('已审核', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '产品评价'
        verbose_name_plural = '产品评价'

    def __str__(self):
        return f"{self.product.name} - {self.customer.get_full_name() or self.customer.username} - {self.rating}星"


class StockChange(models.Model):
    """库存变动记录"""
    ACTION_CHOICES = [
        ('increase', '增加'),
        ('decrease', '减少'),
        ('adjust', '调整'),
        ('reserve', '预留'),
        ('release', '释放'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_changes')
    quantity = models.IntegerField('变动数量')
    action = models.CharField('操作类型', max_length=20, choices=ACTION_CHOICES)
    current_stock = models.PositiveIntegerField('变动后库存')
    reference = models.CharField('关联单号', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '库存变动'
        verbose_name_plural = '库存变动'

    def __str__(self):
        return f"{self.product.name} - {self.get_action_display()} {self.quantity}"