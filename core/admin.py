from django.contrib import admin

from .models import Committee, Member, Entry


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_paid', 'created_at']
    list_editable = ['is_paid']


admin.site.register(Member)
admin.site.register(Entry)
