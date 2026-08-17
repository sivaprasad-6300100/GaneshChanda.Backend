from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Committee, Member, Entry, OtpVerification, Expense
from . import otp_utils


class SendSignupOtpSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError('Enter a valid 10-digit phone number.')
        if Member.objects.filter(phone=value).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return value

    def save(self):
        phone = self.validated_data['phone']
        try:
            verification_id = otp_utils.send_otp(phone)
        except otp_utils.OtpError as e:
            raise serializers.ValidationError({'detail': str(e)})
        OtpVerification.objects.update_or_create(
            phone=phone, defaults={'verification_id': verification_id}
        )
        return phone


class SignupSerializer(serializers.Serializer):
    """Creates a new Committee plus its first (admin) Member. Requires a
    verified OTP for the phone number."""
    committee_name = serializers.CharField(max_length=150)
    name = serializers.CharField(max_length=150)
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    otp = serializers.CharField(write_only=True, max_length=8)

    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError('Enter a valid 10-digit phone number.')
        if Member.objects.filter(phone=value).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return value

    def validate(self, data):
        phone = data['phone']
        try:
            record = OtpVerification.objects.get(phone=phone)
        except OtpVerification.DoesNotExist:
            raise serializers.ValidationError({'otp': 'Please request an OTP first.'})

        if not record.is_fresh():
            raise serializers.ValidationError({'otp': 'OTP expired. Please request a new one.'})

        try:
            ok = otp_utils.validate_otp(phone, record.verification_id, data['otp'])
        except otp_utils.OtpError as e:
            raise serializers.ValidationError({'otp': str(e)})

        if not ok:
            raise serializers.ValidationError({'otp': 'Incorrect or expired OTP.'})

        return data

    def create(self, validated_data):
        validated_data.pop('otp', None)
        committee = Committee.objects.create(name=validated_data['committee_name'])
        member = Member.objects.create_user(
            phone=validated_data['phone'],
            name=validated_data['name'],
            committee=committee,
            password=validated_data['password'],
        )
        member.is_admin = True
        member.save()
        OtpVerification.objects.filter(phone=validated_data['phone']).delete()
        return member


MEMBER_FREE_LIMIT = 5
MEMBER_PAID_LIMIT = 7


class JoinCommitteeSerializer(serializers.Serializer):
    """Adds a new Member to an existing Committee using its share code."""
    committee_code = serializers.CharField()
    name = serializers.CharField(max_length=150)
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_committee_code(self, value):
        try:
            committee = Committee.objects.get(code=value.strip().upper())
        except Committee.DoesNotExist:
            raise serializers.ValidationError('No committee found with this code. Check with your committee admin.')

        limit = MEMBER_PAID_LIMIT if committee.is_paid else MEMBER_FREE_LIMIT
        if committee.members.count() >= limit:
            raise serializers.ValidationError(
                f'This committee has reached its member limit ({limit}). Ask the admin to upgrade to add more members.'
            )
        return committee

    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError('Enter a valid 10-digit phone number.')
        if Member.objects.filter(phone=value).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return value

    def create(self, validated_data):
        committee = validated_data['committee_code']
        return Member.objects.create_user(
            phone=validated_data['phone'],
            name=validated_data['name'],
            committee=committee,
            password=validated_data['password'],
        )


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(phone=data['phone'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid phone number or password.')
        data['user'] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    """Lightweight reset: confirm phone + committee name match, then set a new
    password. Not OTP-verified - reasonable for a low-stakes community tool,
    not bank-grade security. Upgrade to an OTP-based reset if that matters later."""
    phone = serializers.CharField()
    committee_name = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        try:
            member = Member.objects.get(phone=data['phone'])
        except Member.DoesNotExist:
            raise serializers.ValidationError('No account found with this phone number.')
        if member.committee.name.strip().lower() != data['committee_name'].strip().lower():
            raise serializers.ValidationError('Committee name does not match our records.')
        data['member'] = member
        return data


class MemberMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'phone']


class EntrySerializer(serializers.ModelSerializer):
    logged_by_name = serializers.CharField(source='logged_by.name', read_only=True, default=None)
    logged_by_id = serializers.IntegerField(source='logged_by.id', read_only=True, default=None)

    class Meta:
        model = Entry
        fields = ['id', 'contributor_name', 'mobile', 'amount', 'created_at', 'updated_at', 'logged_by_name', 'logged_by_id']
        read_only_fields = ['id', 'created_at', 'updated_at', 'logged_by_name', 'logged_by_id']

    def validate_mobile(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError('Enter a valid 10-digit mobile number.')
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value


class MemberDetailSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ['id', 'name', 'phone', 'is_admin', 'profile_picture', 'created_at']

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        request = self.context.get('request')
        url = obj.profile_picture.url
        return request.build_absolute_uri(url) if request else url


class CommitteeIconUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Committee
        fields = ['icon']

class CommitteeProfileSerializer(serializers.ModelSerializer):
    members = MemberDetailSerializer(many=True, read_only=True)
    icon =serializers.SerializerMethodField()



    class Meta:
        model = Committee
        fields = ['id', 'name', 'code', 'is_paid', 'icon','created_at', 'members']

    def get_icon(self, obj):
        if not obj.icon:
            return None
        request = self.context.get('request')
        url = obj.icon.url
        return request.build_absolute_uri(url) if request else url


class ProfilePictureUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['profile_picture']


class ExpenseSerializer(serializers.ModelSerializer):
    logged_by_name = serializers.CharField(source='logged_by.name', read_only=True, default=None)
    logged_by_id = serializers.IntegerField(source='logged_by.id', read_only=True, default=None)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'category', 'category_display', 'amount', 'notes',
            'created_at', 'updated_at', 'logged_by_name', 'logged_by_id',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'logged_by_name', 'logged_by_id', 'category_display']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError('Enter a title for this expense.')
        return value