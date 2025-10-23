import logging
from database import get_db
from services.ai_service import extract_watering_info
from services.reminder_service import create_plant_reminder
from utils.time_utils import get_moscow_now, format_days_ago
from utils.season_utils import get_current_season, adjust_watering_interval
from config import STATE_EMOJI, STATE_NAMES

logger = logging.getLogger(__name__)

# Временное хранилище для анализов (будет перенесено в Redis в будущем)
temp_analyses = {}


async def save_analyzed_plant(user_id: int, analysis_data: dict) -> dict:
    """Сохранение проанализированного растения"""
    try:
        raw_analysis = analysis_data.get("analysis", "")
        state_info = analysis_data.get("state_info", {})
        
        watering_info = extract_watering_info(raw_analysis)
        
        # Получаем базовый интервал из AI анализа
        base_interval = watering_info["interval_days"]
        
        # Корректируем интервал с учетом сезона
        season_info = get_current_season()
        adjusted_interval = adjust_watering_interval(base_interval, season_info['season'])
        
        logger.info(f"🌍 Сезон: {season_info['season_ru']}, Базовый интервал: {base_interval} дней, Скорректированный: {adjusted_interval} дней")
        
        db = await get_db()
        plant_id = await db.save_plant(
            user_id=user_id,
            analysis=raw_analysis,
            photo_file_id=analysis_data["photo_file_id"],
            plant_name=analysis_data.get("plant_name", "Неизвестное растение")
        )
        
        # Устанавливаем скорректированный интервал полива
        await db.update_plant_watering_interval(plant_id, adjusted_interval)
        
        # Сохраняем состояние растения
        current_state = state_info.get('current_state', 'healthy')
        state_reason = state_info.get('state_reason', 'Первичный анализ AI')
        
        await db.update_plant_state(
            plant_id=plant_id,
            user_id=user_id,
            new_state=current_state,
            change_reason=state_reason,
            photo_file_id=analysis_data["photo_file_id"],
            ai_analysis=raw_analysis,
            watering_adjustment=state_info.get('watering_adjustment', 0),
            feeding_adjustment=state_info.get('feeding_adjustment'),
            recommendations=state_info.get('recommendations', '')
        )
        
        # Сохраняем полный анализ в историю
        await db.save_full_analysis(
            plant_id=plant_id,
            user_id=user_id,
            photo_file_id=analysis_data["photo_file_id"],
            full_analysis=raw_analysis,
            confidence=analysis_data.get("confidence", 0),
            identified_species=analysis_data.get("plant_name"),
            detected_state=current_state,
            watering_advice=watering_info.get("personal_recommendations"),
            lighting_advice=None
        )
        
        # Создаем напоминание с учетом сезона
        await create_plant_reminder(plant_id, user_id, adjusted_interval)
        
        plant_name = analysis_data.get("plant_name", "растение")
        state_emoji = STATE_EMOJI.get(current_state, '🌱')
        state_name = STATE_NAMES.get(current_state, 'Здоровое')
        
        return {
            "success": True,
            "plant_id": plant_id,
            "plant_name": plant_name,
            "state": current_state,
            "state_emoji": state_emoji,
            "state_name": state_name,
            "interval": adjusted_interval,
            "season": season_info['season_ru']
        }
        
    except Exception as e:
        logger.error(f"Ошибка сохранения растения: {e}")
        return {"success": False, "error": str(e)}


async def update_plant_state_from_photo(plant_id: int, user_id: int, 
                                        photo_file_id: str, state_info: dict, 
                                        raw_analysis: str) -> dict:
    """Обновление состояния растения по новому фото"""
    try:
        db = await get_db()
        plant = await db.get_plant_by_id(plant_id, user_id)
        
        if not plant:
            return {"success": False, "error": "Растение не найдено"}
        
        previous_state = plant.get('current_state', 'healthy')
        new_state = state_info.get('current_state', 'healthy')
        state_reason = state_info.get('state_reason', 'Анализ AI')
        
        state_changed = (new_state != previous_state)
        
        # Обновляем состояние
        await db.update_plant_state(
            plant_id=plant_id,
            user_id=user_id,
            new_state=new_state,
            change_reason=state_reason,
            photo_file_id=photo_file_id,
            ai_analysis=raw_analysis,
            watering_adjustment=state_info.get('watering_adjustment', 0),
            feeding_adjustment=state_info.get('feeding_adjustment'),
            recommendations=state_info.get('recommendations', '')
        )
        
        # Обновляем дату последнего фото
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE plants 
                SET last_photo_analysis = CURRENT_TIMESTAMP,
                    photo_file_id = $1
                WHERE id = $2
            """, photo_file_id, plant_id)
        
        return {
            "success": True,
            "state_changed": state_changed,
            "previous_state": previous_state,
            "new_state": new_state,
            "plant_name": plant['display_name']
        }
        
    except Exception as e:
        logger.error(f"Ошибка обновления состояния: {e}")
        return {"success": False, "error": str(e)}


async def get_user_plants_list(user_id: int, limit: int = 15) -> list:
    """Получить список растений пользователя с форматированием"""
    try:
        db = await get_db()
        plants = await db.get_user_plants(user_id, limit=limit)
        
        formatted_plants = []
        
        for plant in plants:
            plant_data = {
                "id": plant.get('id'),
                "display_name": plant.get('display_name'),
                "type": plant.get('type', 'regular'),
                "emoji": '🌱'
            }
            
            if plant.get('type') == 'growing':
                plant_data["emoji"] = '🌱'
                plant_data["stage_info"] = plant.get('stage_info', 'В процессе')
                plant_data["growing_id"] = plant.get('growing_id')
            else:
                current_state = plant.get('current_state', 'healthy')
                plant_data["emoji"] = STATE_EMOJI.get(current_state, '🌱')
                plant_data["current_state"] = current_state
                plant_data["water_status"] = format_days_ago(plant.get('last_watered'))
            
            formatted_plants.append(plant_data)
        
        return formatted_plants
        
    except Exception as e:
        logger.error(f"Ошибка получения списка растений: {e}")
        return []


async def water_plant(user_id: int, plant_id: int) -> dict:
    """Полить растение"""
    try:
        db = await get_db()
        plant = await db.get_plant_by_id(plant_id, user_id)
        
        if not plant:
            return {"success": False, "error": "Растение не найдено"}
        
        await db.update_watering(user_id, plant_id)
        
        # Получаем интервал с учетом сезона
        base_interval = plant.get('watering_interval', 5)
        season_info = get_current_season()
        
        # Интервал уже должен быть скорректирован в БД, но на всякий случай проверяем
        interval = base_interval
        
        await create_plant_reminder(plant_id, user_id, interval)
        
        current_time = get_moscow_now().strftime("%d.%m.%Y в %H:%M")
        plant_name = plant['display_name']
        
        return {
            "success": True,
            "plant_name": plant_name,
            "time": current_time,
            "next_watering_days": interval
        }
        
    except Exception as e:
        logger.error(f"Ошибка полива: {e}")
        return {"success": False, "error": str(e)}


async def water_all_plants(user_id: int) -> dict:
    """Полить все растения"""
    try:
        db = await get_db()
        await db.update_watering(user_id)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Ошибка массового полива: {e}")
        return {"success": False, "error": str(e)}


async def delete_plant(user_id: int, plant_id: int) -> dict:
    """Удалить растение"""
    try:
        db = await get_db()
        plant = await db.get_plant_by_id(plant_id, user_id)
        
        if not plant:
            return {"success": False, "error": "Растение не найдено"}
        
        plant_name = plant['display_name']
        await db.delete_plant(user_id, plant_id)
        
        return {"success": True, "plant_name": plant_name}
        
    except Exception as e:
        logger.error(f"Ошибка удаления растения: {e}")
        return {"success": False, "error": str(e)}


async def rename_plant(user_id: int, plant_id: int, new_name: str) -> dict:
    """Переименовать растение"""
    try:
        if len(new_name.strip()) < 2:
            return {"success": False, "error": "Слишком короткое название"}
        
        db = await get_db()
        await db.update_plant_name(plant_id, user_id, new_name.strip())
        
        return {"success": True, "new_name": new_name.strip()}
        
    except Exception as e:
        logger.error(f"Ошибка переименования: {e}")
        return {"success": False, "error": str(e)}


async def get_plant_details(plant_id: int, user_id: int) -> dict:
    """Получить детали растения"""
    try:
        db = await get_db()
        plant = await db.get_plant_with_state(plant_id, user_id)
        
        if not plant:
            return None
        
        plant_name = plant['display_name']
        current_state = plant.get('current_state', 'healthy')
        state_emoji = STATE_EMOJI.get(current_state, '🌱')
        state_name = STATE_NAMES.get(current_state, 'Здоровое')
        watering_interval = plant.get('watering_interval', 5)
        state_changes = plant.get('state_changes_count', 0)
        water_status = format_days_ago(plant.get('last_watered'))
        
        return {
            "plant_id": plant_id,
            "plant_name": plant_name,
            "current_state": current_state,
            "state_emoji": state_emoji,
            "state_name": state_name,
            "watering_interval": watering_interval,
            "state_changes_count": state_changes,
            "water_status": water_status
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения деталей: {e}")
        return None


async def get_plant_state_history(plant_id: int, limit: int = 10) -> list:
    """Получить историю изменений состояний"""
    try:
        db = await get_db()
        history = await db.get_plant_state_history(plant_id, limit=limit)
        
        formatted_history = []
        for entry in history:
            formatted_history.append({
                "date": entry.get('change_date'),
                "from_state": entry.get('previous_state'),
                "to_state": entry.get('new_state'),
                "reason": entry.get('change_reason'),
                "emoji_from": STATE_EMOJI.get(entry.get('previous_state'), ''),
                "emoji_to": STATE_EMOJI.get(entry.get('new_state'), '🌱')
            })
        
        return formatted_history
        
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        return []
