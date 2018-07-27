from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from django.shortcuts import get_object_or_404
from accounts.models import User, Team, Project
from .models import Log, Issue, Scrum
from accounts.serializers import (
                                UserSerializer,
                                TeamSerializer,
                                ProjectSerializer
                                )
from .serializers import (
                        LogSerializer,
                        IssueSerializer,
                        ScrumSerializer,
                        ScrumReportSerializer,
                        IssueStatusSerializer
                        )
from scrumbot.mixins import CRUDMixin, ParseMixin
from django.http import QueryDict
from django.conf import settings

class ScrumAPI(APIView, CRUDMixin, ParseMixin):
    """
    Scrum API
    """
    
    def post(self, request, *args, **kwargs):
        """
        adds scrum reports to db
        """
        data = self.parseData(request.POST)

        try:
            Team.objects.get(id=data['team_id'])
        except Team.DoesNotExist:
            team_data = QueryDict('', mutable=True)
            team_data['id'] = data['team_id']
            team_data['domain'] = data['team_domain']
            self.create(team_data, Team, TeamSerializer)

        try:
            user = User.objects.get(slack_id=data['user_id'])
        except User.DoesNotExist:
            user_data = QueryDict('', mutable=True)
            user_data['username'] = data['user_name']
            user_data['team'] = data['team_id']
            user_data['slack_id'] = data['user_id']
            user = self.create(user_data, User, UserSerializer)

        try:
            project = Project.objects.get(id=data['channel_id'])
        except Project.DoesNotExist:
            project_data = QueryDict('', mutable=True)
            project_data['id'] = data['channel_id']
            project_data['name'] = data['channel_name']
            project_data['team'] = data['team_id']
            project = self.create(project_data, Project, ProjectSerializer)

        # user = User.objects.get(slack_id=data['user_id'])
        # project = Project.objects.get(id=data['channel_id'])

        scrum_data = QueryDict('', mutable=True)
        scrum_data['user'] = user.id
        scrum_data['project'] = project.id
        try:
            hoursIndex = data['text'].index("4.")+2
            scrum_data['hours'] = data['text'][hoursIndex:]
            1 / int(scrum_data['hours'])
        except:
            return Response(data="Invalid input format")
        scrum = self.create(scrum_data, Scrum, ScrumSerializer)

        none_strings = ['None', 'none', 'N/A', 'n/a']
        try:
            for idx, log_type in (settings.LOG_TYPES).items():
                log_data = QueryDict('', mutable=True)
                start_index = data['text'].index(str(log_type)+".")+2
                messages = data['text'][start_index:]
                last_index = messages.index(str(log_type+1)+".")
                messages = messages[:last_index]
                splitby_line = messages.split('\r\n')
                log_data['log_type'] = str(log_type)
                for y in range(len(splitby_line)):
                    log_data['scrum'] = scrum.id
                    log_data['message'] = splitby_line[y]
                    if log_data['message'] not in none_strings:
                        self.create(log_data, Log, LogSerializer)
                    if (idx == 'ISSUE' and splitby_line[y] not in none_strings):
                        issue_data = QueryDict('', mutable=True)
                        issue_data['issue'] = splitby_line[y]
                        issue_data['scrum'] = scrum.id
                        self.create(issue_data, Issue, IssueSerializer)
        except:
            return Response(data="Invalid input format")

        return Response(data=data, status=201)

    def get(self, request, *args, **kwargs):
        """
        lists scrum reports
        """
        return self.list_all(Scrum, ScrumReportSerializer, 'date_created')

class IssuesAPI(ViewSet, CRUDMixin):
    """
    Issues API
    """

    def list(self, request, *args, **kwargs):
        """
        lists issue reports
        """
        return self.list_all(Issue, IssueSerializer, 'scrum__date_created')

    def update_status(self, request, *args, **kwargs):
        """
        updates an issue's status
        """
        issue_id = self.kwargs.get('issue_id', None)
        issue = get_object_or_404(Issue, id=issue_id)
        serializer = IssueStatusSerializer(data=self.request.data)
        if serializer.is_valid():
            serializer.update(issue.id)
            issue = get_object_or_404(Issue, id=issue_id)
            serializer = IssueSerializer(issue)
            return Response(serializer.data,status=200)
        return Response(status=400)
        