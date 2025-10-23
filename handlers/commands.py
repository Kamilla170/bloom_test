import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import get_db
from keyboards.main_menu import main_menu
from utils.time_utils import get_moscow_now

logger = logging.getLogger(__name__)
router = Router()


async def show_returning_user_welcome(message: types.Message):
    """Приветствие для возвращающегося пользователя"""
    first_name = message.from_user.first_name or "друг"
    
    await message.answer(
        f"🌱 С возвращением, {first_name}!\n\n"
        "Что будем делать с растениями сегодня?",
        reply_markup=main_menu()
    )


@router.message(Command("start"))
async def start_command(message: types.Message):
    """Команда /start с упрощенным онбордингом"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "друг"
    
    logger.info(f"📩 Получена команда /start от пользователя {user_id}")
    
    try:
        db = await get_db()
        
        async with db.pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT user_id FROM users WHERE user_id = $1", user_id
            )
            
            if not existing_user:
                # Новый пользователь - добавляем в БД
                await db.add_user(
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name
                )
                
                logger.info(f"✅ Новый пользователь {user_id} добавлен")
                
                # Приветствие для нового пользователя
                await message.answer(
                    f"🌱 Привет, {first_name}!\n\n"
                    "Я помогу ухаживать за вашими растениями:\n\n"
                    "📸 Определяю вид по фото и даю рекомендации\n"
                    "💧 Напоминаю о поливе с учетом состояния\n"
                    "🧠 Запоминаю всю историю каждого растения\n"
                    "📊 Отслеживаю изменения по месячным фото\n\n"
                    "🎯 Начните с кнопки \"Добавить растение\" или просто пришлите фото!",
                    reply_markup=main_menu()
                )
            else:
                # Возвращающийся пользователь
                logger.info(f"✅ Возвращающийся пользователь {user_id}")
                await show_returning_user_welcome(message)
                
    except Exception as e:
        logger.error(f"❌ Ошибка /start: {e}", exc_info=True)
        await message.answer(
            f"🌱 Привет, {first_name}!",
            reply_markup=main_menu()
        )


@router.message(Command("help"))
async def help_command(message: types.Message):
    """Команда /help"""
    help_text = """
🌿 <b>Помощь по боту</b>

<b>Основные возможности:</b>

📸 <b>Анализ растений</b>
- Отправьте фото - я определю вид и состояние
- Получите персональные рекомендации
- Сохраните растение для отслеживания

💧 <b>Уход за растениями</b>
- Напоминания о поливе
- Отслеживание состояний (цветение, покой, стресс)
- Месячные обновления фото

🌱 <b>Выращивание с нуля</b>
- Дневник роста
- Фотоистория развития
- Пошаговые инструкции

❓ <b>Вопросы о растениях</b>
- Задайте вопрос с фото
- Получите ответ с учетом истории
- Сохраните в базу знаний

📊 <b>Статистика</b>
- Количество растений
- История анализов
- База знаний

<b>Команды:</b>
/start - Главное меню
/help - Эта справка
/stats - Моя статистика

💡 <b>Совет:</b> Просто отправьте фото растения - я сразу его распознаю!
"""
    
    await message.answer(help_text, parse_mode="HTML", reply_markup=main_menu())


@router.message(Command("stats"))
async def stats_command(message: types.Message):
    """Команда /stats - показать статистику пользователя"""
    user_id = message.from_user.id
    
    try:
        db = await get_db()
        
        async with db.pool.acquire() as conn:
            # Считаем растения
            plants_count = await conn.fetchval(
                "SELECT COUNT(*) FROM plants WHERE user_id = $1",
                user_id
            )
            
            # Считаем анализы
            analyses_count = await conn.fetchval(
                "SELECT COUNT(*) FROM plant_analyses WHERE user_id = $1",
                user_id
            )
            
            # Считаем вопросы
            questions_count = await conn.fetchval(
                "SELECT COUNT(*) FROM plant_qa_history WHERE user_id = $1",
                user_id
            )
            
            # Считаем выращивания
            growing_count = await conn.fetchval(
                "SELECT COUNT(*) FROM growing_plants WHERE user_id = $1",
                user_id
            )
            
            # Получаем дату регистрации
            user_info = await conn.fetchrow(
                "SELECT created_at FROM users WHERE user_id = $1",
                user_id
            )
            
            created_at = user_info['created_at']
            days_with_bot = (get_moscow_now().replace(tzinfo=None) - created_at).days
        
        stats_text = f"""
📊 <b>Ваша статистика</b>

🌿 <b>Растения:</b> {plants_count}
📸 <b>Анализов:</b> {analyses_count}
❓ <b>Вопросов:</b> {questions_count}
🌱 <b>Выращиваю:</b> {growing_count}

📅 <b>С ботом:</b> {days_with_bot} дней
🎯 <b>Активность:</b> {analyses_count + questions_count} действий

💡 Продолжайте ухаживать за растениями!
"""
        
        await message.answer(stats_text, parse_mode="HTML", reply_markup=main_menu())
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка получения статистики",
            reply_markup=main_menu()
        )


@router.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    """Команда /cancel - отмена текущего действия"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Нет активных действий для отмены", reply_markup=main_menu())
        return
    
    await state.clear()
    await message.answer("✅ Действие отменено", reply_markup=main_menu())
