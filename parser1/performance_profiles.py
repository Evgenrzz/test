#!/usr/bin/env python3
"""
Профили производительности для различных сценариев использования
"""
from .config import *

# Профиль "Быстрый" - минимальные проверки, максимальная скорость
FAST_PROFILE = {
    'ENABLE_SHA256_CHECK': False,
    'ENABLE_FUZZY_MATCHING': False,
    'ENABLE_SIZE_CHECK': False,
    'ENABLE_DETAILED_LOGGING': False
}

# Профиль "Сбалансированный" - оптимальное соотношение скорости и точности
BALANCED_PROFILE = {
    'ENABLE_SHA256_CHECK': True,
    'ENABLE_FUZZY_MATCHING': True,
    'ENABLE_SIZE_CHECK': False,  # Отключаем проверку по размеру для скорости
    'ENABLE_DETAILED_LOGGING': True
}

# Профиль "Точный" - максимальная точность, все проверки включены
ACCURATE_PROFILE = {
    'ENABLE_SHA256_CHECK': True,
    'ENABLE_FUZZY_MATCHING': True,
    'ENABLE_SIZE_CHECK': True,
    'ENABLE_DETAILED_LOGGING': True
}

# Профиль "Отладка" - все включено для анализа
DEBUG_PROFILE = {
    'ENABLE_SHA256_CHECK': True,
    'ENABLE_FUZZY_MATCHING': True,
    'ENABLE_SIZE_CHECK': True,
    'ENABLE_DETAILED_LOGGING': True
}

def apply_performance_profile(profile_name):
    """Применяем профиль производительности"""
    profiles = {
        'fast': FAST_PROFILE,
        'balanced': BALANCED_PROFILE,
        'accurate': ACCURATE_PROFILE,
        'debug': DEBUG_PROFILE
    }
    
    if profile_name not in profiles:
        raise ValueError(f"Неизвестный профиль: {profile_name}. Доступные: {list(profiles.keys())}")
    
    profile = profiles[profile_name]
    
    # Обновляем глобальные переменные
    globals()['ENABLE_SHA256_CHECK'] = profile['ENABLE_SHA256_CHECK']
    globals()['ENABLE_FUZZY_MATCHING'] = profile['ENABLE_FUZZY_MATCHING']
    globals()['ENABLE_SIZE_CHECK'] = profile['ENABLE_SIZE_CHECK']
    globals()['ENABLE_DETAILED_LOGGING'] = profile['ENABLE_DETAILED_LOGGING']
    
    print(f"🚀 Применен профиль производительности: {profile_name}")
    print(f"   SHA-256: {'✅' if profile['ENABLE_SHA256_CHECK'] else '❌'}")
    print(f"   Fuzzy matching: {'✅' if profile['ENABLE_FUZZY_MATCHING'] else '❌'}")
    print(f"   Size check: {'✅' if profile['ENABLE_SIZE_CHECK'] else '❌'}")
    print(f"   Detailed logging: {'✅' if profile['ENABLE_DETAILED_LOGGING'] else '❌'}")

def get_performance_estimate(profile_name):
    """Получаем оценку производительности для профиля"""
    estimates = {
        'fast': {
            'description': 'Максимальная скорость',
            'overhead_per_file': '0.1-0.2 сек',
            'accuracy': '70%',
            'use_case': 'Быстрая обработка больших объемов'
        },
        'balanced': {
            'description': 'Оптимальное соотношение',
            'overhead_per_file': '0.3-0.5 сек',
            'accuracy': '90%',
            'use_case': 'Рекомендуемый для большинства случаев'
        },
        'accurate': {
            'description': 'Максимальная точность',
            'overhead_per_file': '0.5-1.0 сек',
            'accuracy': '98%',
            'use_case': 'Критически важные данные'
        },
        'debug': {
            'description': 'Полная диагностика',
            'overhead_per_file': '0.5-1.0 сек',
            'accuracy': '98%',
            'use_case': 'Отладка и анализ'
        }
    }
    
    return estimates.get(profile_name, estimates['balanced'])
