# -*- coding: utf-8 -*-
import asyncio
import uuid

import gradio as gr

from src.config import settings, validate_settings
from src.models.schemas import CandidateProfile
from src.graph.interview_graph import create_interview_graph
from src.utils.logger import InterviewLogger


class InterviewApp:
    """Менеджер интервью с поддержкой множественных сессий"""
    
    def __init__(self):
        self.graph = create_interview_graph()
        self.logger = InterviewLogger()
        self.sessions = {}  # session_id -> state
        self.graph.set_logger(self.logger)
    
    async def start(self, profile, session_id):
        log_path = self.logger.start_session(session_id)
        print(f"Session {session_id}: {log_path}")
        
        state = await self.graph.start_interview(profile, session_id)
        self.sessions[session_id] = state
        return state
    
    async def process(self, session_id, message):
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        state = await self.graph.process_user_message(state, message)
        self.sessions[session_id] = state
        return state
    
    def get_state(self, session_id):
        return self.sessions.get(session_id)
    
    def get_thoughts(self, session_id):
        state = self.sessions.get(session_id)
        if state:
            return self.logger.get_internal_thoughts_display(state)
        return ""
    
    def format_feedback(self, feedback):
        return self.logger.format_final_feedback(feedback) if feedback else ""


# Один экземпляр приложения
app = None


def get_app():
    global app
    if app is None:
        app = InterviewApp()
    return app


async def start_interview_async(name, position, grade, experience, session_id):
    interview_app = get_app()
    
    profile = CandidateProfile(
        name=name or "Кандидат",
        position=position or "Backend Developer",
        target_grade=grade or "Junior",
        experience=experience or "Без опыта"
    )
    
    new_session_id = str(uuid.uuid4())[:8]
    
    try:
        state = await interview_app.start(profile, new_session_id)
        greet_msg = state.get("current_agent_message", "Привет!")
        thoughts = interview_app.get_thoughts(new_session_id)
        
        chat = [{"role": "assistant", "content": greet_msg}]
        return chat, "Интервью начато", thoughts, "", new_session_id
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], f"Ошибка: {e}", "", "", None


def start_interview(name, position, grade, experience, session_id):
    return asyncio.run(start_interview_async(name, position, grade, experience, session_id))


async def send_message_async(message, chat_history, session_id):
    if not session_id:
        return chat_history, "Сначала начните интервью", "", "", session_id
    
    if not message.strip():
        return chat_history, "Введите сообщение", "", "", session_id
    
    interview_app = get_app()
    
    try:
        state = await interview_app.process(session_id, message)
        resp = state.get("current_agent_message", "")
        status = state.get("status", "")
        final_feedback = state.get("final_feedback")
        
        fullResp = resp
        qh = state.get("question_handler_response")
        if qh and qh not in resp:
            fullResp = f"{qh}\n\n{resp}" if resp else qh
        
        chat_history = chat_history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": fullResp}
        ]
        
        thoughts = interview_app.get_thoughts(session_id)
        
        feedback_display = ""
        if final_feedback:
            feedback_display = interview_app.format_feedback(final_feedback)
            if interview_app.logger.current_session_log_path:
                feedback_display += f"\n\nЛог: {interview_app.logger.current_session_log_path}"
        
        status_msg = "Завершено" if status == "completed" else "В процессе"
        return chat_history, status_msg, thoughts, feedback_display, session_id
        
    except ValueError as e:
        return chat_history, str(e), "", "", session_id
    except Exception as e:
        import traceback
        traceback.print_exc()
        return chat_history, f"Ошибка: {e}", "", "", session_id


def send_message(message, chat_history, session_id):
    return asyncio.run(send_message_async(message, chat_history, session_id))


async def stop_interview_async(chat_history, session_id):
    if not session_id:
        return chat_history, "Нет активного интервью", "", "", session_id
    
    interview_app = get_app()
    
    try:
        state = await interview_app.process(session_id, "Стоп интервью")
        final_feedback = state.get("final_feedback")
        
        chat_history = chat_history + [
            {"role": "user", "content": "Стоп интервью"},
            {"role": "assistant", "content": "Интервью завершено. Формирую отчет..."}
        ]
        
        thoughts = interview_app.get_thoughts(session_id)
        
        feedback_display = ""
        if final_feedback:
            feedback_display = interview_app.format_feedback(final_feedback)
            if interview_app.logger.current_session_log_path:
                feedback_display += f"\n\nЛог: {interview_app.logger.current_session_log_path}"
        
        return chat_history, "Завершено", thoughts, feedback_display, session_id
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return chat_history, f"Ошибка: {e}", "", "", session_id


def stop_interview(chat_history, session_id):
    return asyncio.run(stop_interview_async(chat_history, session_id))



def save_log(session_id):
    if not session_id:
        return "Нет данных"
    
    interview_app = get_app()
    state = interview_app.get_state(session_id)
    
    if not state:
        return "Сессия не найдена"
    
    try:
        path = interview_app.logger.save_session_with_timestamp(state)
        return f"Лог: {path}"
    except Exception as e:
        return f"Ошибка: {e}"


def create_ui():
    with gr.Blocks(title="Interview Coach") as demo:
        session_state = gr.State(value=None)
        
        gr.Markdown("""
        # Multi-Agent Interview Coach
        Система технического интервью с AI-агентами.
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Кандидат")
                
                with gr.Row():
                    name_input = gr.Textbox(label="Имя", value="Алекс")
                    position_input = gr.Textbox(label="Позиция", value="Backend Developer")
                
                with gr.Row():
                    grade_dropdown = gr.Dropdown(label="Грейд", choices=["Junior", "Middle", "Senior"], value="Junior")
                    experience_input = gr.Textbox(label="Опыт", value="Django, SQL")
                
                start_btn = gr.Button("Начать", variant="primary")
                
                gr.Markdown("### Диалог")
                chatbot = gr.Chatbot(label="Чат", height=400)
                
                with gr.Row():
                    msg_input = gr.Textbox(label="Ответ", placeholder="...", scale=4)
                    send_btn = gr.Button("Отправить", variant="primary", scale=1)
                
                with gr.Row():
                    stop_btn = gr.Button("Стоп", variant="stop")
                    save_btn = gr.Button("Сохранить лог")
                
                status_text = gr.Textbox(label="Статус", interactive=False)
            
            with gr.Column(scale=1):
                gr.Markdown("### Мысли агентов")
                thoughts_display = gr.Textbox(label="Reflection", lines=15, interactive=False)
                
                gr.Markdown("### Отчёт")
                feedback_display = gr.Textbox(label="Feedback", lines=20, interactive=False)
        
        # Обработчики событий
        start_btn.click(
            fn=start_interview,
            inputs=[name_input, position_input, grade_dropdown, experience_input, session_state],
            outputs=[chatbot, status_text, thoughts_display, feedback_display, session_state]
        )
        
        send_btn.click(
            fn=send_message,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, status_text, thoughts_display, feedback_display, session_state]
        ).then(fn=lambda: "", outputs=[msg_input])
        
        msg_input.submit(
            fn=send_message,
            inputs=[msg_input, chatbot, session_state],
            outputs=[chatbot, status_text, thoughts_display, feedback_display, session_state]
        ).then(fn=lambda: "", outputs=[msg_input])
        
        stop_btn.click(
            fn=stop_interview,
            inputs=[chatbot, session_state],
            outputs=[chatbot, status_text, thoughts_display, feedback_display, session_state]
        )
        
        save_btn.click(
            fn=save_log,
            inputs=[session_state],
            outputs=[status_text]
        )
        
        gr.Markdown("""
        ---
        **Подсказки:** Скажите ложное ("Python 4.0 удалит циклы"), задайте вопрос ("Какие задачи?"), уйдите от темы.
        """)
    
    return demo


def main():
    errors = validate_settings()
    if errors:
        print("Ошибки конфигурации:")
        for e in errors:
            print(f"  - {e}")
        return
    
    # Инициализация приложения
    get_app()
    
    print(f"Starting... model={settings.openai_model}")
    if settings.openai_base_url:
        print(f"Proxy: {settings.openai_base_url}")
    
    demo = create_ui()
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
