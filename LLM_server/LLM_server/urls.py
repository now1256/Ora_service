"""
URL configuration for LLM_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.LLM_server.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from ai.interface import views
from ai.utils import LangChain
from ai import monitoring_views

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # 새로운 클린 아키텍처 API
    path('api/process-text/', views.process_text, name='process_text'),
    path('api/rag/reload/', LangChain.RAG_RELOAD, name='RAG_RELOAD'),
    path('api/vectorstore/delete/', LangChain.VECTORSTORE_DELETE, name='VECTORSTORE_DELETE'),
    
    # Ultra Fast LLM 모니터링 및 관리 API
    path('api/health/', monitoring_views.health_check, name='health_check'),
    path('api/stats/', monitoring_views.system_stats, name='system_stats'),
    path('api/dashboard/', monitoring_views.performance_dashboard, name='performance_dashboard'),
    path('api/report/', monitoring_views.performance_report, name='performance_report'),
    path('api/optimize/', monitoring_views.optimize_system, name='optimize_system'),
    path('api/cache/stats/', monitoring_views.cache_stats, name='cache_stats'),
    path('api/cache/clear/', monitoring_views.clear_cache, name='clear_cache'),
    path('api/llm/health/', monitoring_views.llm_health, name='llm_health'),
    path('api/test/speed/', monitoring_views.test_response_speed, name='test_response_speed'),
    path('api/initialize/', monitoring_views.initialize_system, name='initialize_system'),
    path('api/monitoring/', monitoring_views.monitoring_summary, name='monitoring_summary')
]
