# main/admin.py
from django.contrib import admin
from django.db import transaction
from django.core.mail import send_mail
from .models import MemberProfile, WorkoutPlan, DietPlan, ProgressEntry, Payment

@admin.action(description='Approve selected payments and activate member')
def approve_payments(modeladmin, request, queryset):
    approved = 0
    with transaction.atomic():
        for payment in queryset.select_for_update():
            if payment.status != 'Approved':
                payment.status = 'Approved'
                payment.save()  # save payment status
                member = payment.member
                member.is_payment_approved = True
                member.save()   # persist profile change
                approved += 1
                # Optional: send email (uncomment after you configure EMAIL settings)
                # if member.user.email:
                #     send_mail(
                #         subject="Payment Approved",
                #         message="Your payment has been approved. You can now access your plan.",
                #         from_email="noreply@example.com",
                #         recipient_list=[member.user.email],
                #         fail_silently=True,
                #     )
    modeladmin.message_user(request, f"{approved} payment(s) approved and member(s) activated.")

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id','member','amount','status','tx_id','created_at')
    list_filter = ('status','created_at')
    search_fields = ('member__user__username','tx_id')
    actions = [approve_payments]

    def save_model(self, request, obj, form, change):
        """
        When editing a single Payment in admin, if status changed to Approved ensure member profile is activated.
        """
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            if obj.status == 'Approved':
                member = obj.member
                if not member.is_payment_approved:
                    member.is_payment_approved = True
                    member.save()
                    # Optional: notify user
                    # if member.user.email:
                    #     send_mail("Payment Approved", "Your payment has been approved.", "noreply@example.com", [member.user.email], fail_silently=True)

# register other models
admin.site.register(MemberProfile)
admin.site.register(WorkoutPlan)
admin.site.register(DietPlan)
admin.site.register(ProgressEntry)
admin.site.register(Payment, PaymentAdmin)
