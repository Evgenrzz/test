#!/usr/bin/env python3
"""
Анализатор дублей для parser2
Специализирован для работы с модифицированными приложениями
"""
import time
from .version_utils import VersionUtils


class DuplicateAnalyzer:
    """Анализатор дублей для модифицированных приложений"""
    
    def __init__(self):
        self.version_utils = VersionUtils()
        self.duplicates_found = []
        self.similar_apps_found = []
    
    def log_duplicate_found(self, duplicate_type, app_name, version, reason):
        """Логируем найденный дубль"""
        duplicate_info = {
            'type': duplicate_type,
            'app_name': app_name,
            'version': version,
            'reason': reason,
            'timestamp': time.time()
        }
        
        self.duplicates_found.append(duplicate_info)
        
        print(f"🔍 Найден дубль ({duplicate_type}): {app_name} v{version}")
        print(f"   Причина: {reason}")
    
    def log_similar_app_found(self, app_name, similar_app, similarity_score):
        """Логируем найденное похожее приложение"""
        similar_info = {
            'app_name': app_name,
            'similar_app': similar_app,
            'similarity_score': similarity_score,
            'timestamp': time.time()
        }
        
        self.similar_apps_found.append(similar_info)
        
        print(f"🔍 Найдено похожее приложение: {app_name} ~ {similar_app}")
        print(f"   Коэффициент схожести: {similarity_score:.2f}")
    
    def analyze_duplicates(self, app_name, version, file_size, sha256_hash=None):
        """Анализируем дубли для модифицированного приложения"""
        print(f"🔍 Анализируем дубли для: {app_name} v{version}")
        
        analysis = {
            'app_name': app_name,
            'version': version,
            'file_size': file_size,
            'sha256_hash': sha256_hash,
            'duplicates': [],
            'similar_apps': [],
            'recommendations': []
        }
        
        # Анализируем дубли по содержимому
        if sha256_hash:
            content_duplicate = self._analyze_content_duplicate(sha256_hash)
            if content_duplicate:
                analysis['duplicates'].append(content_duplicate)
                self.log_duplicate_found('content', app_name, version, 'Точное совпадение содержимого файла')
        
        # Анализируем дубли по размеру
        size_duplicate = self._analyze_size_duplicate(file_size)
        if size_duplicate:
            analysis['duplicates'].append(size_duplicate)
            self.log_duplicate_found('size', app_name, version, 'Похожий размер файла')
        
        # Анализируем похожие приложения
        similar_apps = self._analyze_similar_apps(app_name)
        if similar_apps:
            analysis['similar_apps'] = similar_apps
            for similar in similar_apps:
                self.log_similar_app_found(app_name, similar['name'], similar['similarity'])
        
        # Генерируем рекомендации
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_content_duplicate(self, sha256_hash):
        """Анализируем дубль по содержимому файла"""
        # Здесь должна быть логика проверки SHA-256 в базе данных
        # Пока что возвращаем None
        return None
    
    def _analyze_size_duplicate(self, file_size, tolerance_percent=5):
        """Анализируем дубль по размеру файла"""
        # Здесь должна быть логика проверки размера в базе данных
        # Пока что возвращаем None
        return None
    
    def _analyze_similar_apps(self, app_name):
        """Анализируем похожие приложения"""
        # Здесь должна быть логика поиска похожих приложений в базе данных
        # Пока что возвращаем пустой список
        return []
    
    def _generate_recommendations(self, analysis):
        """Генерируем рекомендации на основе анализа"""
        recommendations = []
        
        if analysis['duplicates']:
            recommendations.append("Обнаружены дубли - рекомендуется проверить уникальность")
        
        if analysis['similar_apps']:
            recommendations.append("Найдены похожие приложения - рекомендуется проверить различия")
        
        if not recommendations:
            recommendations.append("Дубли не обнаружены - файл уникален")
        
        return recommendations
    
    def get_statistics(self):
        """Получаем статистику анализа"""
        return {
            'duplicates_found': len(self.duplicates_found),
            'similar_apps_found': len(self.similar_apps_found),
            'total_analyzed': len(self.duplicates_found) + len(self.similar_apps_found)
        }
    
    def reset_statistics(self):
        """Сбрасываем статистику"""
        self.duplicates_found = []
        self.similar_apps_found = []
        print("🔄 Статистика анализа дублей сброшена")
    
    def print_summary(self):
        """Выводим сводку анализа"""
        stats = self.get_statistics()
        
        print("\n📊 Сводка анализа дублей:")
        print(f"   Дубли найдены: {stats['duplicates_found']}")
        print(f"   Похожие приложения: {stats['similar_apps_found']}")
        print(f"   Всего проанализировано: {stats['total_analyzed']}")
        
        if self.duplicates_found:
            print("\n🔍 Найденные дубли:")
            for dup in self.duplicates_found:
                print(f"   - {dup['app_name']} v{dup['version']} ({dup['type']})")
        
        if self.similar_apps_found:
            print("\n🔍 Похожие приложения:")
            for sim in self.similar_apps_found:
                print(f"   - {sim['app_name']} ~ {sim['similar_app']} ({sim['similarity_score']:.2f})")

