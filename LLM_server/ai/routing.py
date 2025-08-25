from django.urls import re_path
from .integration import chat_consumer, ask, llama,v1,v2,v2_eos,v2_update ,qwen,gptoss, gptossupdate

websocket_urlpatterns = [
    # RAG 없는 경로
    #re_path(r'^ws/LlamaAsk/$', ask.ChatConsumer.as_asgi()), 
    #re_path(r'^ws/LlamaAsk/$', gptoss.ChatConsumer.as_asgi()), 
    re_path(r'^ws/LlamaAsk/$', gptossupdate.ChatConsumer.as_asgi()), 
    

    #re_path(r'ws/LlamaAsk/$', v1.VoiceChatConsumer.as_asgi()),
    #re_path(r'ws/LlamaAsk/$', v2_eos.VoiceChatConsumer.as_asgi()),
    #re_path(r'^ws/LlamaAsk/$', qwen.ChatConsumer.as_asgi()),

    #re_path(r'^ws/LlamaAsk/$', llama.ChatConsumer.as_asgi()), 
    
    # RAG 접목한 경로 -> 현재 서버에서 오류남 
    re_path(r'^ws/ask/$', chat_consumer.ChatConsumer.as_asgi()),
]
