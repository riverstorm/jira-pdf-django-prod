from django.db import models


class Client(models.Model):
    key = models.CharField(max_length=250)
    shared_secret = models.TextField()
    oauth_client_id = models.TextField(null=True, blank=True)
    public_key = models.TextField(null=True, blank=True)
    base_url = models.TextField()
    display_url = models.TextField(null=True, blank=True)
    display_url_servicedesk = models.TextField(null=True, blank=True)
    product_type = models.CharField(max_length=250)
    description = models.TextField(null=True, blank=True)
    service_entitlement_number = models.CharField(max_length=250, null=True, blank=True)
    custom_template = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class User(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=250)


class UserSettings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    issue_path = models.BooleanField(default=True)
    title = models.BooleanField(default=True)
    description = models.BooleanField(default=True)
    status = models.BooleanField(default=True)
    attachments = models.BooleanField(default=True)
    attachments_links = models.BooleanField(default=True)
    comments = models.BooleanField(default=True)
    users = models.BooleanField(default=True)
    images = models.BooleanField(default=False)
    comment_images = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Generation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now=True)
    size_kb = models.IntegerField()
    time_seconds = models.IntegerField()
    time_issue = models.IntegerField()
    time_images = models.IntegerField()
    time_attachments = models.IntegerField()
    time_build = models.IntegerField()
    images_sum = models.IntegerField()
