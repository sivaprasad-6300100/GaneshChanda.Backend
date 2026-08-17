from django.urls import path
from rest_framework import views
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ExpenseCategoryStatsView, ExpenseDetailView, ExpenseListCreateView, MemberCollectionStatsView, ProfileView, RemoveMemberView, SendSignupOtpView, SignupView, JoinCommitteeView, LoginView, ForgotPasswordView,
    EntryListCreateView, EntryDetailView, CheckDuplicateView,
    StatsView, MembersView, ExportCsvView, UpdateProfilePictureView,UpdateCommitteeIconView
)

urlpatterns = [
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/join/', JoinCommitteeView.as_view(), name='join'),
    path('auth/login/', LoginView.as_view(), name='login'),
    # path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('entries/', EntryListCreateView.as_view(), name='entries'),
    path('entries/<int:pk>/', EntryDetailView.as_view(), name='entry-detail'),
    path('entries/check-duplicate/', CheckDuplicateView.as_view(), name='check-duplicate'),
    path('entries/export/', ExportCsvView.as_view(), name='export'),
    path('stats/', StatsView.as_view(), name='stats'),
    path('members/', MembersView.as_view(), name='members'),
    path('member-collections/', MemberCollectionStatsView.as_view(), name='member-collections'),
    path('auth/send-signup-otp/', SendSignupOtpView.as_view(), name='send-signup-otp'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/picture/', UpdateProfilePictureView.as_view(), name='profile-picture'),
    path('expenses/', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('expenses/<int:pk>/', ExpenseDetailView.as_view(), name='expense-detail'),
    path('expenses/by-category/', ExpenseCategoryStatsView.as_view(), name='expense-by-category'),
    path('members/<int:pk>/', RemoveMemberView.as_view(), name='remove-member'),    
    path('committee/icon/', UpdateCommitteeIconView.as_view()),
    
]
