import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import m2m_changed, post_migrate, pre_save
from django.dispatch import receiver


ROLE_PERMISSIONS = {
    'Admin': None,
    'Manager': (
        'view_product', 'add_product', 'change_product',
        'view_category', 'add_category', 'change_category',
        'view_order', 'change_order', 'view_orderitem',
        'view_invoice', 'change_invoice', 'view_paymentattempt',
    ),

    'Product Creator': (
        'view_product', 'add_product', 'change_product',
        'view_category', 'add_category', 'change_category',
        'view_productimage', 'add_productimage', 'change_productimage',
    ),

    'Order Manager': (
        'view_order', 'change_order', 'view_orderitem', 'change_orderitem',
        'view_invoice', 'change_invoice', 'view_invoiceitem',
        'view_paymentattempt', 'change_paymentattempt',
        'view_refund', 'change_refund',
    ),

    'Support': ('view_order', 'view_orderitem', 'view_address'),
}

security_logger = logging.getLogger('shop.security')


@receiver(post_migrate)
def create_business_groups(sender, **kwargs):
    if sender.name != 'shop':
        return

    for group_name, codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        if codenames is None:
            group.permissions.set(Permission.objects.filter(content_type__app_label='shop'))
        elif codenames:
            permissions = Permission.objects.filter(content_type__app_label='shop', codename__in=codenames)
            group.permissions.set(permissions)


@receiver(pre_save, sender=get_user_model())
def log_account_status_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    previous = sender.objects.filter(pk=instance.pk).values('is_active').first()

    if previous and previous['is_active'] != instance.is_active:
        security_logger.info('security_event=account_status_changed user_id=%s', instance.pk)


@receiver(m2m_changed, sender=get_user_model().groups.through)
def log_group_membership_change(sender, instance, action, pk_set, **kwargs):
    if action in {'post_add', 'post_remove', 'post_clear'}:
        security_logger.info('security_event=group_membership_changed user_id=%s', instance.pk)


@receiver(m2m_changed, sender=Group.permissions.through)
def log_group_permission_change(sender, instance, action, pk_set, **kwargs):
    if action in {'post_add', 'post_remove', 'post_clear'}:
        security_logger.info('security_event=group_permissions_changed group_id=%s', instance.pk)
