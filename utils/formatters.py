from config import STATE_EMOJI, STATE_NAMES, STATE_RECOMMENDATIONS

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
    """Получить рекомендации для состояния растения"""
    template = STATE_RECOMMENDATIONS.get(state, STATE_RECOMMENDATIONS['healthy'])
    return template.format(plant_name=plant_name)
