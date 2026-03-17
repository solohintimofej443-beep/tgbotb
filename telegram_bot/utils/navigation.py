"""Утилиты для управления историей состояний (навигацией)"""

from telegram.ext import ContextTypes


class NavigationHistory:
    """Класс для управления историей навигации"""
    
    HISTORY_KEY = 'navigation_history'
    
    @staticmethod
    def add_state(context: ContextTypes.DEFAULT_TYPE, state: str, data: dict = None):
        """Добавить новое состояние в историю"""
        if NavigationHistory.HISTORY_KEY not in context.user_data:
            context.user_data[NavigationHistory.HISTORY_KEY] = []
        
        state_entry = {
            'state': state,
            'data': data or {}
        }
        context.user_data[NavigationHistory.HISTORY_KEY].append(state_entry)
    
    @staticmethod
    def go_back(context: ContextTypes.DEFAULT_TYPE) -> dict:
        """Вернуться к предыдущему состоянию"""
        history = context.user_data.get(NavigationHistory.HISTORY_KEY, [])
        
        if len(history) > 1:
            # Удалить текущее состояние
            history.pop()
            # Вернуть предыдущее
            return history[-1] if history else None
        
        return None
    
    @staticmethod
    def get_current_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
        """Получить текущее состояние"""
        history = context.user_data.get(NavigationHistory.HISTORY_KEY, [])
        return history[-1] if history else None
    
    @staticmethod
    def clear_history(context: ContextTypes.DEFAULT_TYPE):
        """Очистить историю"""
        if NavigationHistory.HISTORY_KEY in context.user_data:
            context.user_data[NavigationHistory.HISTORY_KEY] = []
    
    @staticmethod
    def has_previous(context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверить есть ли предыдущее состояние"""
        history = context.user_data.get(NavigationHistory.HISTORY_KEY, [])
        return len(history) > 1
