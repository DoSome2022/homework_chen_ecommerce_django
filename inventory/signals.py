# inventory/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
import logging
from .models import StockReservation

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def cleanup_expired_reservations(sender, **kwargs):
    """清理过期的库存预留"""
    if sender.name != 'inventory':
        return
    
    try:
        expired_reservations = StockReservation.objects.filter(
            status__in=['reserved', 'partially_reserved'],
            expires_at__lt=timezone.now()
        )
        
        count = expired_reservations.count()
        if count > 0:
            with transaction.atomic():
                for reservation in expired_reservations:
                    # 释放库存
                    from .services import InventoryService
                    InventoryService.release_stock(reservation.id)
                
                logger.info(f'清理了 {count} 个过期的库存预留')
    
    except Exception as e:
        logger.error(f'清理过期库存预留失败: {str(e)}')