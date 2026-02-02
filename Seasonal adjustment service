"""
Сервис сезонной корректировки интервалов полива
Запускается 1 числа каждого месяца, спрашивает GPT о новых интервалах
"""

import logging
from openai import AsyncOpenAI
from typing import List, Dict

from database import get_db
from config import OPENAI_API_KEY
from utils.season_utils import get_current_season

logger = logging.getLogger(__name__)

# Инициализация OpenAI клиента
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def get_seasonal_watering_interval(plant_name: str, base_interval: int, season_info: dict) -> int:
    """
    Спросить GPT какой интервал полива нужен для растения в текущем сезоне
    
    Args:
        plant_name: название растения
        base_interval: базовый (летний) интервал полива
        season_info: информация о текущем сезоне
        
    Returns:
        int: новый интервал полива в днях
    """
    if not openai_client:
        logger.warning("⚠️ OpenAI недоступен, используем формулу")
        return calculate_interval_by_formula(base_interval, season_info['season'])
    
    try:
        prompt = f"""Ты - эксперт по комнатным растениям. 

Растение: {plant_name}
Базовый летний интервал полива: {base_interval} дней
Текущий сезон: {season_info['season_ru']} ({season_info['month_name_ru']})
Фаза роста: {season_info['growth_phase']}

Учитывая особенности этого вида растения и текущий сезон, какой должен быть интервал полива?

ВАЖНО:
- Зимой большинство растений требуют полива в 1.5-2.5 раза реже
- Суккуленты и кактусы зимой почти не поливают (раз в 3-4 недели)
- Тропические растения зимой тоже сокращают полив, но меньше
- Цветущие растения требуют больше воды даже зимой

Ответь ТОЛЬКО ОДНИМ ЧИСЛОМ - количество дней между поливами.
Число должно быть от 3 до 28."""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Используем дешёвую модель для простых запросов
            messages=[
                {"role": "system", "content": "Ты эксперт по уходу за комнатными растениями. Отвечай только числом."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Извлекаем число из ответа
        import re
        numbers = re.findall(r'\d+', answer)
        if numbers:
            interval = int(numbers[0])
            # Валидация
            interval = max(3, min(28, interval))
            logger.info(f"✅ GPT: {plant_name} → {interval} дней ({season_info['season_ru']})")
            return interval
        else:
            logger.warning(f"⚠️ GPT не вернул число для {plant_name}: '{answer}'")
            return calculate_interval_by_formula(base_interval, season_info['season'])
            
    except Exception as e:
        logger.error(f"❌ Ошибка GPT для {plant_name}: {e}")
        return calculate_interval_by_formula(base_interval, season_info['season'])


def calculate_interval_by_formula(base_interval: int, season: str) -> int:
    """
    Fallback: рассчитать интервал по формуле если GPT недоступен
    """
    multipliers = {
        'winter': 2.0,
        'spring': 1.0,
        'summer': 0.8,
        'autumn': 1.4
    }
    
    multiplier = multipliers.get(season, 1.0)
    adjusted = int(round(base_interval * multiplier))
    
    return max(3, min(28, adjusted))


async def adjust_all_plants_for_season():
    """
    Главная функция: пересчитать интервалы полива для всех растений
    Запускается 1 числа каждого месяца
    """
    try:
        logger.info("=" * 60)
        logger.info("🌍 СЕЗОННАЯ КОРРЕКТИРОВКА ИНТЕРВАЛОВ ПОЛИВА")
        logger.info("=" * 60)
        
        season_info = get_current_season()
        logger.info(f"📅 Месяц: {season_info['month_name_ru']}")
        logger.info(f"🌍 Сезон: {season_info['season_ru']}")
        logger.info(f"🌱 Фаза: {season_info['growth_phase']}")
        
        db = await get_db()
        
        async with db.pool.acquire() as conn:
            # Получаем все активные растения с базовым интервалом
            plants = await conn.fetch("""
                SELECT 
                    p.id,
                    p.user_id,
                    COALESCE(p.custom_name, p.plant_name, 'Растение #' || p.id) as display_name,
                    p.plant_name,
                    COALESCE(p.base_watering_interval, p.watering_interval, 7) as base_interval,
                    p.watering_interval as current_interval
                FROM plants p
                WHERE p.plant_type = 'regular'
                  AND p.reminder_enabled = TRUE
                ORDER BY p.user_id, p.id
            """)
            
            logger.info(f"📊 Найдено растений для обработки: {len(plants)}")
            
            if not plants:
                logger.info("✅ Нет растений для корректировки")
                return
            
            updated_count = 0
            error_count = 0
            
            # Группируем по пользователям для оптимизации
            current_user_id = None
            
            for plant in plants:
                try:
                    plant_id = plant['id']
                    user_id = plant['user_id']
                    plant_name = plant['plant_name'] or plant['display_name']
                    base_interval = plant['base_interval']
                    current_interval = plant['current_interval']
                    
                    # Логируем смену пользователя
                    if user_id != current_user_id:
                        current_user_id = user_id
                        logger.info(f"👤 Пользователь {user_id}:")
                    
                    # Получаем новый интервал от GPT
                    new_interval = await get_seasonal_watering_interval(
                        plant_name, 
                        base_interval, 
                        season_info
                    )
                    
                    # Обновляем только если изменился
                    if new_interval != current_interval:
                        await conn.execute("""
                            UPDATE plants 
                            SET watering_interval = $1
                            WHERE id = $2
                        """, new_interval, plant_id)
                        
                        # Пересоздаём напоминание с новым интервалом
                        from services.reminder_service import create_plant_reminder
                        await create_plant_reminder(plant_id, user_id, new_interval)
                        
                        logger.info(f"   🌱 {plant['display_name']}: {current_interval} → {new_interval} дней")
                        updated_count += 1
                    else:
                        logger.info(f"   🌱 {plant['display_name']}: без изменений ({current_interval} дней)")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"   ❌ Ошибка для растения {plant['id']}: {e}")
            
            logger.info("=" * 60)
            logger.info(f"✅ КОРРЕКТИРОВКА ЗАВЕРШЕНА")
            logger.info(f"📊 Обновлено: {updated_count} из {len(plants)}")
            if error_count:
                logger.info(f"❌ Ошибок: {error_count}")
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА сезонной корректировки: {e}", exc_info=True)


async def set_base_interval_for_plant(plant_id: int, base_interval: int):
    """
    Установить базовый (летний) интервал полива для растения
    Вызывается при добавлении нового растения
    """
    try:
        db = await get_db()
        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE plants 
                SET base_watering_interval = $1
                WHERE id = $2
            """, base_interval, plant_id)
            
        logger.info(f"✅ Базовый интервал {base_interval} дней установлен для растения {plant_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка установки базового интервала: {e}")


async def migrate_base_intervals():
    """
    Миграция: установить base_watering_interval для существующих растений
    Запускается один раз
    """
    try:
        logger.info("🔄 Миграция базовых интервалов полива...")
        
        db = await get_db()
        season_info = get_current_season()
        
        async with db.pool.acquire() as conn:
            # Добавляем колонку если её нет
            await conn.execute("""
                ALTER TABLE plants 
                ADD COLUMN IF NOT EXISTS base_watering_interval INTEGER
            """)
            
            # Получаем растения без базового интервала
            plants = await conn.fetch("""
                SELECT id, watering_interval, plant_name
                FROM plants
                WHERE base_watering_interval IS NULL
                  AND plant_type = 'regular'
            """)
            
            if not plants:
                logger.info("✅ Все растения уже имеют базовый интервал")
                return
            
            logger.info(f"📊 Найдено растений без базового интервала: {len(plants)}")
            
            # Рассчитываем базовый интервал из текущего
            # Если сейчас зима и интервал 10, то базовый = 10 / 2.0 = 5
            reverse_multipliers = {
                'winter': 0.5,   # Делим на 2 чтобы получить летний
                'spring': 1.0,
                'summer': 1.25,  # Умножаем на 1.25 чтобы получить летний
                'autumn': 0.7
            }
            
            multiplier = reverse_multipliers.get(season_info['season'], 1.0)
            
            for plant in plants:
                current = plant['watering_interval'] or 7
                base = int(round(current * multiplier))
                base = max(3, min(14, base))  # Базовый летний интервал 3-14 дней
                
                await conn.execute("""
                    UPDATE plants 
                    SET base_watering_interval = $1
                    WHERE id = $2
                """, base, plant['id'])
                
                logger.info(f"   🌱 {plant['plant_name'] or f'Растение #{plant['id']}'}: "
                          f"текущий {current} → базовый {base} дней")
            
            logger.info(f"✅ Миграция завершена: {len(plants)} растений обновлено")
            
    except Exception as e:
        logger.error(f"❌ Ошибка миграции базовых интервалов: {e}", exc_info=True)
