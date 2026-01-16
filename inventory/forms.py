# inventory/forms.py
from django import forms
from .models import Warehouse, WarehouseZone, WarehouseAisle, WarehouseShelf,Inventory,  StorageLocation
from django.core.exceptions import ValidationError
from django.utils import timezone

class WarehouseForm(forms.ModelForm):
    """倉庫表單"""
    class Meta:
        model = Warehouse
        fields = [
            'code', 'name', 'location', 
            'contact_person', 'phone', 'email', 'address',
            'total_capacity', 'warehouse_type', 'manager', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如: WH001'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '倉庫名稱'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '地理位置'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '聯絡人姓名'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '聯絡電話'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '電子郵件'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '詳細地址'
            }),
            'total_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '總容量 (m³)',
                'step': '0.01'
            }),
            'warehouse_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'manager': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'code': '倉庫代碼',
            'name': '倉庫名稱',
            'location': '地理位置',
            'contact_person': '聯絡人',
            'phone': '聯絡電話',
            'email': '電子郵件',
            'address': '詳細地址',
            'total_capacity': '總容量 (m³)',
            'warehouse_type': '倉庫類型',
            'manager': '負責人',
            'is_active': '是否啟用'
        }

    def clean_code(self):
        """驗證倉庫代碼唯一性"""
        code = self.cleaned_data['code']
        if Warehouse.objects.filter(code=code).exists():
            raise forms.ValidationError('此倉庫代碼已被使用，請使用其他代碼')
        return code

    def clean_total_capacity(self):
        """驗證總容量"""
        total_capacity = self.cleaned_data['total_capacity']
        if total_capacity <= 0:
            raise forms.ValidationError('總容量必須大於0')
        return total_capacity


class WarehouseZoneForm(forms.ModelForm):
    """倉庫區域表單"""
    class Meta:
        model = WarehouseZone
        fields = [
            'name', 'code', 'zone_type',
            'total_capacity', 'temperature_controlled',
            'min_temperature', 'max_temperature',
            'requires_access_code', 'access_level_required',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '區域名稱'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '區域代碼'
            }),
            'zone_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'total_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'temperature_controlled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'min_temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '最低溫度 (℃)'
            }),
            'max_temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '最高溫度 (℃)'
            }),
            'requires_access_code': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'access_level_required': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class WarehouseAisleForm(forms.ModelForm):
    """倉庫通道表單"""
    class Meta:
        model = WarehouseAisle
        fields = [
            'aisle_number', 'name',
            'length', 'width', 'height',
            'has_pallets', 'max_weight_capacity',
            'is_active'
        ]
        widgets = {
            'aisle_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如: A01'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '通道名稱 (可選)'
            }),
            'length': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'width': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'has_pallets': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'max_weight_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class WarehouseShelfForm(forms.ModelForm):
    """倉庫貨架表單"""
    class Meta:
        model = WarehouseShelf
        fields = [
            'shelf_number', 'name', 'shelf_type',
            'levels', 'bays', 'depth',
            'max_weight_per_level', 'max_items_per_bay',
            'is_active'
        ]
        widgets = {
            'shelf_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如: S01'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '貨架名稱 (可選)'
            }),
            'shelf_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'levels': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'bays': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'depth': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_weight_per_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_items_per_bay': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class WarehouseCreationFormSet:
    """倉庫創建表單集"""
    def __init__(self, data=None, warehouse=None):
        self.warehouse_form = WarehouseForm(data)
        self.zone_forms = []
        self.aisle_forms = []
        self.shelf_forms = []
        
        if data:
            # 處理區域表單
            for i in range(int(data.get('zone_count', 0))):
                prefix = f'zone_{i}'
                self.zone_forms.append(WarehouseZoneForm(data, prefix=prefix))
            
            # 處理通道表單
            for i in range(int(data.get('aisle_count', 0))):
                prefix = f'aisle_{i}'
                self.aisle_forms.append(WarehouseAisleForm(data, prefix=prefix))
            
            # 處理貨架表單
            for i in range(int(data.get('shelf_count', 0))):
                prefix = f'shelf_{i}'
                self.shelf_forms.append(WarehouseShelfForm(data, prefix=prefix))
        
    def is_valid(self):
        """驗證所有表單"""
        if not self.warehouse_form.is_valid():
            return False
        
        for form in self.zone_forms:
            if not form.is_valid():
                return False
        
        for form in self.aisle_forms:
            if not form.is_valid():
                return False
        
        for form in self.shelf_forms:
            if not form.is_valid():
                return False
        
        return True
    
    def save(self, user):
        """保存所有表單"""
        # 保存倉庫
        warehouse = self.warehouse_form.save(commit=False)
        warehouse.used_capacity = 0
        if user and hasattr(user, 'staff'):
            warehouse.manager = user.staff
        warehouse.save()
        
        # 保存區域
        zones = []
        for zone_form in self.zone_forms:
            zone = zone_form.save(commit=False)
            zone.warehouse = warehouse
            zone.save()
            zones.append(zone)
        
        # 保存通道
        aisles = []
        for aisle_form in self.aisle_forms:
            aisle = aisle_form.save(commit=False)
            aisle.warehouse = warehouse
            if zones:
                # 分配區域（簡單輪詢）
                zone = zones[len(aisles) % len(zones)]
                aisle.zone = zone
            aisle.save()
            aisles.append(aisle)
        
        # 保存貨架
        for shelf_form in self.shelf_forms:
            shelf = shelf_form.save(commit=False)
            if aisles:
                # 分配通道
                aisle = aisles[len(self.shelf_forms) % len(aisles)]
                shelf.aisle = aisle
            shelf.save()
        
        return warehouse
    

class InventoryForm(forms.ModelForm):
    """库存记录表单"""
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='仓库',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.none(),  # 初始为空，动态填充
        label='存储位置',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    batch_number = forms.CharField(
        label='批次号',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '自动生成或手动输入'})
    )
    
    manufacturing_date = forms.DateField(
        label='生产日期',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    expiry_date = forms.DateField(
        label='过期日期',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 初始化位置字段的 queryset 為空
        self.fields['location'].queryset = StorageLocation.objects.none()
        
        # 只有在 POST 數據中有 warehouse 時才更新位置選項
        if 'warehouse' in self.data:
            try:
                warehouse_id = int(self.data.get('warehouse'))
                self.fields['location'].queryset = StorageLocation.objects.filter(
                    warehouse_id=warehouse_id,
                    is_active=True,
                    is_full=False
                )
            except (ValueError, TypeError):
                pass
    
    class Meta:
        model = Inventory
        fields = [
            'product', 'warehouse', 'location', 'quantity',
            'batch_number', 'manufacturing_date', 'expiry_date',
            'unit_cost', 'status'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '请输入数量'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0,
                'placeholder': '单位成本'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise ValidationError('数量必须大于0')
        return quantity
    
    def clean_unit_cost(self):
        unit_cost = self.cleaned_data['unit_cost']
        if unit_cost <= 0:
            raise ValidationError('单位成本必须大于0')
        return unit_cost
    
    def clean(self):
        cleaned_data = super().clean()
        warehouse = cleaned_data.get('warehouse')
        location = cleaned_data.get('location')
        quantity = cleaned_data.get('quantity', 0)
        product = cleaned_data.get('product')
        
        if location and warehouse:
            if location.warehouse != warehouse:
                raise ValidationError('所选位置不属于所选仓库')
            
            # 检查位置容量
            if product:
                product_volume = product.volume if hasattr(product, 'volume') else 0
                required_volume = quantity * product_volume
                
                if product_volume > 0 and location.available_volume < required_volume:
                    raise ValidationError(f'位置容量不足。需要: {required_volume}m³, 可用: {location.available_volume}m³')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 如果没有批次号，自动生成
        if not instance.batch_number and instance.product:
            date_str = timezone.now().strftime('%Y%m%d')
            product_sku = instance.product.sku
            instance.batch_number = f'{product_sku}-{date_str}'
        
        if commit:
            instance.save()
            
            # 更新位置占用情况
            if instance.location and instance.product:
                product_volume = instance.product.volume if hasattr(instance.product, 'volume') else 0
                volume = instance.quantity * product_volume
                weight = 0  # 这里可以根据产品重量计算
                
                if volume > 0:
                    instance.location.update_occupancy(volume, weight, 'increase')
                    instance.warehouse.update_capacity(volume, 'increase')
        
        return instance
class InventorySearchForm(forms.Form):
    """库存搜索表单"""
    product_name = forms.CharField(
        label='产品名称',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '输入产品名称'
        })
    )
    
    sku = forms.CharField(
        label='SKU',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '输入SKU'
        })
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='仓库',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', '所有状态')] + Inventory.STATUS_CHOICES,
        label='状态',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    low_stock = forms.BooleanField(
        label='仅显示低库存',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def filter_queryset(self, queryset):
        """应用过滤条件"""
        if self.is_valid():
            product_name = self.cleaned_data.get('product_name')
            sku = self.cleaned_data.get('sku')
            warehouse = self.cleaned_data.get('warehouse')
            status = self.cleaned_data.get('status')
            low_stock = self.cleaned_data.get('low_stock')
            
            if product_name:
                queryset = queryset.filter(product__name__icontains=product_name)
            
            if sku:
                queryset = queryset.filter(product__sku__icontains=sku)
            
            if warehouse:
                queryset = queryset.filter(warehouse=warehouse)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if low_stock:
                # 查找可用数量小于或等于低库存阈值的产品
                from django.db.models import F
                queryset = queryset.filter(
                    available_quantity__lte=F('product__low_stock_threshold')
                )
        
        return queryset


class QuickAddInventoryForm(forms.Form):
    """快速添加入库表单（非 ModelForm）"""
    sku = forms.CharField(
        label='SKU',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '扫描或输入SKU',
            'autofocus': True
        })
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label='仓库',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    quantity = forms.IntegerField(
        label='数量',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    batch_number = forms.CharField(
        label='批次号',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '可选，自动生成'
        })
    )
    
    unit_cost = forms.DecimalField(
        label='单位成本',
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '可选，使用产品成本价'
        })
    )
    
    def clean_sku(self):
        sku = self.cleaned_data['sku']
        from products.models import Product
        try:
            product = Product.objects.get(sku=sku)
            return sku
        except Product.DoesNotExist:
            raise ValidationError(f'找不到SKU为 {sku} 的产品')