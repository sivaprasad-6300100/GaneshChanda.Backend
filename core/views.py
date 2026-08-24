import csv

from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser



from .models import Entry, Expense, Member
from .serializers import (
    CommitteeIconUpdateSerializer, SignupSerializer, JoinCommitteeSerializer, LoginSerializer,
    ForgotPasswordSerializer, EntrySerializer, MemberMiniSerializer, SendSignupOtpSerializer,
    MemberDetailSerializer, CommitteeProfileSerializer, ProfilePictureUpdateSerializer,ExpenseSerializer,
)


class IsOwnerOrAdmin(permissions.BasePermission):
    message = 'You can only edit or delete items you logged yourself.'

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        return obj.logged_by_id == request.user.id


    

FREE_LIMIT = 30


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def auth_payload(member):
    return {
        'committee_name': member.committee.name,
        'committee_code': member.committee.code,
        'member_id': member.id,
        'member_name': member.name,
        'phone': member.phone,
        'is_admin': member.is_admin,
        **tokens_for_user(member),
    }


class SignupView(generics.GenericAPIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(auth_payload(member), status=status.HTTP_201_CREATED)


class JoinCommitteeView(generics.GenericAPIView):
    serializer_class = JoinCommitteeSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(auth_payload(member), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.validated_data['user']
        return Response(auth_payload(member))


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.validated_data['member']
        member.set_password(serializer.validated_data['new_password'])
        member.save()
        return Response({'detail': 'Password updated. You can log in now.'})


class EntryListCreateView(generics.ListCreateAPIView):
    serializer_class = EntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Entry.objects.filter(committee=self.request.user.committee)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(contributor_name__icontains=search) | Q(mobile__icontains=search))
        return qs

    def perform_create(self, serializer):
        committee = self.request.user.committee
        count = Entry.objects.filter(committee=committee).count()
        if count >= FREE_LIMIT and not committee.is_paid:
            raise ValidationError({'detail': f'Free limit of {FREE_LIMIT} entries reached. Upgrade to add more.'})
        serializer.save(committee=committee, logged_by=self.request.user)


class EntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        return Entry.objects.filter(committee=self.request.user.committee)


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        return Expense.objects.filter(committee=self.request.user.committee)


class CheckDuplicateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        mobile = request.query_params.get('mobile', '')
        existing = Entry.objects.filter(committee=request.user.committee, mobile=mobile).first()
        if existing:
            return Response({
                'duplicate': True,
                'existing_amount': existing.amount,
                'existing_name': existing.contributor_name,
            })
        return Response({'duplicate': False})


class StatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        committee = request.user.committee
        entries = Entry.objects.filter(committee=committee)
        expenses = Expense.objects.filter(committee=committee)
        total = sum(e.amount for e in entries)
        total_spent = sum(e.amount for e in expenses)
        count = entries.count()
        return Response({
            'total': total,
            'total_spent': total_spent,
            'count': count,
            'free_limit': FREE_LIMIT,
            'free_remaining': max(FREE_LIMIT - count, 0),
            'is_paid_required': count >= FREE_LIMIT and not committee.is_paid,
            'is_paid': committee.is_paid,
            'committee_code': committee.code,
            'expense_count': expenses.count(),
            'net_balance': total - total_spent,
        })


class MembersView(generics.ListAPIView):
    serializer_class = MemberMiniSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Member.objects.filter(committee=self.request.user.committee)


class ExportCsvView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        entries = Entry.objects.filter(committee=request.user.committee).order_by('created_at')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="chanda_entries.csv"'
        writer = csv.writer(response)
        writer.writerow(['Contributor Name', 'Mobile', 'Amount', 'Logged By', 'Date'])
        for e in entries:
            writer.writerow([
                e.contributor_name, e.mobile, e.amount,
                e.logged_by.name if e.logged_by else '',
                e.created_at.strftime('%Y-%m-%d %H:%M'),
            ])
        return response



class MemberCollectionStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        committee = request.user.committee
        breakdown = (
            Entry.objects.filter(committee=committee)
            .values('logged_by_id', 'logged_by__name')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        return Response([
            {
                'member_id': row['logged_by_id'],
                'member_name': row['logged_by__name'] or 'Unknown',
                'total': row['total'],
                'count': row['count'],
            }
            for row in breakdown
        ])




class SendSignupOtpView(generics.GenericAPIView):
    serializer_class = SendSignupOtpSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'OTP sent.'})



class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        committee = request.user.committee
        data = CommitteeProfileSerializer(committee, context={'request': request}).data
        data['me'] = MemberDetailSerializer(request.user, context={'request': request}).data
        return Response(data)


class UpdateProfilePictureView(generics.UpdateAPIView):
    serializer_class = ProfilePictureUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

class RemoveMemberView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Member.objects.filter(committee=self.request.user.committee)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return Response(
                {'detail': 'Only the committee admin can remove members.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        member = self.get_object()
        if member.id == request.user.id:
            return Response(
                {'detail': 'You cannot remove yourself from the committee.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().delete(request, *args, **kwargs)



class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Expense.objects.filter(committee=self.request.user.committee)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(notes__icontains=search))
        return qs

    def perform_create(self, serializer):
        serializer.save(committee=self.request.user.committee, logged_by=self.request.user)







class ExpenseCategoryStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        committee = request.user.committee
        breakdown = (
            Expense.objects.filter(committee=committee)
            .values('category')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        category_labels = dict(Expense.CATEGORY_CHOICES)
        return Response([
            {
                'category': row['category'],
                'category_display': category_labels.get(row['category'], row['category']),
                'total': row['total'],
                'count': row['count'],
            }
            for row in breakdown
        ])



class UpdateCommitteeIconView(generics.UpdateAPIView):
    serializer_class = CommitteeIconUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user.committee

    def patch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return Response(
                {'detail': 'Only the committee admin can change the group icon.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().patch(request, *args, **kwargs)