from config import STATE_EMOJI, STATE_NAMES

def format_plant_analysis(raw_text: str, confidence: float = None, state_info: dict = None) -> str:
    """Форматирование анализа с состоянием"""
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    formatted = ""
    
    plant_name = "Неизвестное растение"
    confidence_level = confidence or 0
    
    for line in lines:
        if line.startswith("РАСТЕНИЕ:"):
            plant_name = line.replace("РАСТЕНИЕ:", "").strip()
            display_name = plant_name.split("(")[0].strip()
            formatted += f"🌿 <b>{display_name}</b>\n"
            if "(" in plant_name:
                latin_name = plant_name[plant_name.find("(")+1:plant_name.find(")")]
                formatted += f"🏷️ <i>{latin_name}</i>\n"
            
        elif line.startswith("УВЕРЕННОСТЬ:"):
            conf = line.replace("УВЕРЕННОСТЬ:", "").strip()
            try:
                confidence_level = float(conf.replace("%", ""))
                if confidence_level >= 80:
                    conf_icon = "🎯"
                elif confidence_level >= 60:
                    conf_icon = "🎪"
                else:
                    conf_icon = "🤔"
                formatted += f"{conf_icon} <b>Уверенность:</b> {conf}\n\n"
            except:
                formatted += f"🎪 <b>Уверенность:</b> {conf}\n\n"
        
        elif line.startswith("ТЕКУЩЕЕ_СОСТОЯНИЕ:"):
            pass
        
        elif line.startswith("СОСТОЯНИЕ:"):
            condition = line.replace("СОСТОЯНИЕ:", "").strip()
            if any(word in condition.lower() for word in ["здоров", "хорош", "отличн", "норм"]):
                icon = "✅"
            elif any(word in condition.lower() for word in ["проблем", "болен", "плох", "стресс"]):
                icon = "⚠️"
            else:
                icon = "ℹ️"
            formatted += f"{icon} <b>Общее состояние:</b> {condition}\n\n"
        
        elif line.startswith("ПОЛИВ_АНАЛИЗ:"):
            analysis = line.replace("ПОЛИВ_АНАЛИЗ:", "").strip()
            if "невозможно" in analysis.lower() or "не видна" in analysis.lower():
                icon = "❓"
            else:
                icon = "💧"
            formatted += f"{icon} <b>Анализ полива:</b> {analysis}\n"
            
        elif line.startswith("ПОЛИВ_РЕКОМЕНДАЦИИ:"):
            recommendations = line.replace("ПОЛИВ_РЕКОМЕНДАЦИИ:", "").strip()
            formatted += f"💡 <b>Рекомендации:</b> {recommendations}\n"
            
        elif line.startswith("ПОЛИВ_ИНТЕРВАЛ:"):
            interval = line.replace("ПОЛИВ_ИНТЕРВАЛ:", "").strip()
            formatted += f"⏰ <b>Интервал полива:</b> каждые {interval} дней\n\n"
            
        elif line.startswith("СВЕТ:"):
            light = line.replace("СВЕТ:", "").strip()
            formatted += f"☀️ <b>Освещение:</b> {light}\n"
            
        elif line.startswith("ТЕМПЕРАТУРА:"):
            temp = line.replace("ТЕМПЕРАТУРА:", "").strip()
            formatted += f"🌡️ <b>Температура:</b> {temp}\n"
            
        elif line.startswith("ВЛАЖНОСТЬ:"):
            humidity = line.replace("ВЛАЖНОСТЬ:", "").strip()
            formatted += f"💨 <b>Влажность:</b> {humidity}\n"
            
        elif line.startswith("ПОДКОРМКА:"):
            feeding = line.replace("ПОДКОРМКА:", "").strip()
            formatted += f"🍽️ <b>Подкормка:</b> {feeding}\n"
        
        elif line.startswith("СОВЕТ:"):
            advice = line.replace("СОВЕТ:", "").strip()
            formatted += f"\n💡 <b>Персональный совет:</b> {advice}"
        
        elif line.startswith("СЕЗОННЫЙ_СОВЕТ:"):
            seasonal_advice = line.replace("СЕЗОННЫЙ_СОВЕТ:", "").strip()
            formatted += f"\n\n🌍 <b>Важно для текущего сезона:</b> {seasonal_advice}"
    
    if state_info:
        current_state = state_info.get('current_state', 'healthy')
        state_emoji = STATE_EMOJI.get(current_state, '🌱')
        state_name = STATE_NAMES.get(current_state, 'Здоровое')
        
        formatted = f"\n{state_emoji} <b>Текущее состояние:</b> {state_name}\n" + formatted
        
        if state_info.get('state_reason'):
            formatted += f"\n📋 <b>Почему:</b> {state_info['state_reason']}"
    
    if confidence_level >= 80:
        formatted += "\n\n🏆 <i>Высокая точность распознавания</i>"
    elif confidence_level >= 60:
        formatted += "\n\n👍 <i>Хорошее распознавание</i>"
    else:
        formatted += "\n\n🤔 <i>Требуется дополнительная идентификация</i>"
    
    formatted += "\n💾 <i>Сохраните для отслеживания изменений!</i>"
    
    return formatted


def get_state_recommendations(state: str, plant_name: str = "растение") -> str:
    """Получить рекомендации для состояния"""
    recommendations = {
        'flowering': f"""
💐 <b>{plant_name} цветет!</b>

<b>Изменения в уходе:</b>
• 💧 <b>Полив:</b> Чаще на 2 дня (больше воды при цветении)
• 🍽️ <b>Подкормка:</b> Удобрение для цветения 1 раз в неделю
• ☀️ <b>Свет:</b> Больше света, но избегайте прямых лучей
• 🌡️ <b>Температура:</b> Стабильная, без перепадов

⚠️ <b>Важно:</b> Не перемещайте растение во время цветения!
💡 <b>Совет:</b> Удаляйте увядшие цветы для продления цветения
""",
        'active_growth': f"""
🌿 <b>{plant_name} активно растет!</b>

<b>Изменения в уходе:</b>
• 💧 <b>Полив:</b> Регулярный, не допускайте пересыхания
• 🍽️ <b>Подкормка:</b> Каждые 2 недели удобрением для роста
• ☀️ <b>Свет:</b> Максимум света для фотосинтеза
• 🪴 <b>Пересадка:</b> Если корням тесно - пересадите

💡 <b>Совет:</b> Это лучшее время для формирования кроны
""",
        'dormancy': f"""
😴 <b>{plant_name} в периоде покоя</b>

<b>Изменения в уходе:</b>
• 💧 <b>Полив:</b> Реже на 5 дней (минимальный полив)
• 🍽️ <b>Подкормка:</b> Прекратить до весны
• 🌡️ <b>Температура:</b> Прохладнее 15-18°C
• ☀️ <b>Свет:</b> Меньше света - это нормально

💡 <b>Совет:</b> Весной растение проснется с новыми силами!
⚠️ Не тревожьте растение в этот период
""",
        'stress': f"""
⚠️ <b>Внимание! {plant_name} в стрессе</b>

<b>Срочные действия:</b>
• 🔍 <b>Диагностика:</b> Определите причину (полив/свет/вредители)
• 💧 <b>Полив:</b> Проверьте влажность - корректируйте режим
• ✂️ <b>Обрезка:</b> Удалите поврежденные листья
• 🦠 <b>Вредители:</b> Осмотрите листья с двух сторон
• 💨 <b>Проветривание:</b> Улучшите циркуляцию воздуха

📸 <b>Важно:</b> Загрузите фото через 3-5 дней для контроля!
❓ Если не помогает - задайте вопрос с фото проблемы
""",
        'adaptation': f"""
🔄 <b>{plant_name} адаптируется</b>

<b>Щадящий режим:</b>
• 💧 <b>Полив:</b> Умеренный, без переувлажнения
• ☀️ <b>Свет:</b> Не ставьте на яркое солнце сразу
• 🌡️ <b>Температура:</b> Стабильная, без стресса
• ⏰ <b>Время:</b> Дайте 2-3 недели на привыкание

💡 <b>Совет:</b> Не пересаживайте и не тревожьте растение
📸 Сфотографируйте через неделю для контроля состояния
""",
        'healthy': f"""
🌱 <b>{plant_name} здоровое!</b>

<b>Продолжайте текущий уход:</b>
• 💧 Регулярный полив по графику
• 🍽️ Подкормка по сезону
• ☀️ Достаточно света
• 🌡️ Комфортная температура

💡 <b>Совет:</b> Продолжайте в том же духе!
📸 Обновляйте фото раз в месяц для отслеживания
"""
    }
    
    return recommendations.get(state, recommendations['healthy'])
