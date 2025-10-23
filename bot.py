import asyncio
import logging
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

# Импорты конфигурации
from config import (
    BOT_TOKEN, WEBHOOK_URL, PORT, MOSCOW_TZ, 
    validate_config, logger
)

# Импорты инициализации
from database import init_database, get_db

# Импорты сервисов
from services.reminder_service import (
    check_and_send_reminders, 
    check_monthly_photo_reminders
)
from services.admin_stats_service import send_daily_report_to_admins

# Импорты handlers
from handlers import (
    commands, photo, callbacks, plants, 
    questions, feedback, onboarding, growing
)

# Импорт middleware
from middleware import ActivityTrackingMiddleware

# Настройка логирования уже в config
logger.info("🚀 Запуск Bloom AI Bot...")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Планировщик
scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)


async def on_startup():
    """Инициализация при запуске"""
    try:
        # Валидация конфигурации
        validate_config()
        
        # Инициализация базы данных
        await init_database()
        logger.info("✅ База данных инициализирована")
        
        # Удаление старого webhook
        logger.info("🔧 Удаление старого webhook...")
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.warning(f"⚠️ Найден активный webhook: {webhook_info.url}")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook удален")
        else:
            logger.info("ℹ️ Webhook не был установлен")
        
        # Регистрация middleware
        register_middleware()
        
        # Регистрация handlers
        register_handlers()
        
        # Настройка планировщика
        setup_scheduler()
        
        # Установка webhook или polling
        if WEBHOOK_URL:
            await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
            logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}/webhook")
        else:
            logger.info("✅ Polling mode активирован")
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        raise


async def on_shutdown():
    """Завершение работы"""
    logger.info("🛑 Остановка бота...")
    
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏰ Планировщик остановлен")
    
    try:
        db = await get_db()
        await db.close()
        logger.info("✅ База данных закрыта")
    except:
        pass
    
    try:
        await bot.session.close()
        logger.info("✅ Сессия бота закрыта")
    except:
        pass


def register_middleware():
    """Регистрация middleware"""
    # Регистрируем middleware для отслеживания активности
    dp.message.middleware(ActivityTrackingMiddleware())
    dp.callback_query.middleware(ActivityTrackingMiddleware())
    
    logger.info("✅ Middleware зарегистрированы (Activity Tracking)")


def register_handlers():
    """Регистрация всех handlers"""
    dp.include_router(commands.router)
    dp.include_router(photo.router)
    dp.include_router(plants.router)
    dp.include_router(questions.router)
    dp.include_router(feedback.router)
    dp.include_router(growing.router)
    dp.include_router(callbacks.router)
    
    logger.info("✅ Handlers зарегистрированы")


def setup_scheduler():
    """Настройка планировщика задач"""
    # Ежедневные напоминания о поливе в 9:00 МСК
    scheduler.add_job(
        lambda: check_and_send_reminders(bot),
        'cron',
        hour=9,
        minute=0,
        id='reminder_check',
        replace_existing=True
    )
    
    # Месячные напоминания об обновлении фото в 10:00 МСК
    scheduler.add_job(
        lambda: check_monthly_photo_reminders(bot),
        'cron',
        hour=10,
        minute=0,
        id='monthly_reminder_check',
        replace_existing=True
    )
    
    # Ежедневная статистика для администраторов в 9:00 МСК
    scheduler.add_job(
        lambda: send_daily_report_to_admins(bot),
        'cron',
        hour=9,
        minute=0,
        id='daily_stats_report',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("🔔 Планировщик запущен")
    logger.info("⏰ Ежедневные напоминания: 9:00 МСК")
    logger.info("📸 Месячные напоминания: 10:00 МСК")
    logger.info("📊 Ежедневная статистика: 9:00 МСК")


async def webhook_handler(request):
    """Webhook обработчик"""
    try:
        url = str(request.url)
        index = url.rfind('/')
        token = url[index + 1:]
        
        if token == BOT_TOKEN.split(':')[1]:
            update = types.Update.model_validate(await request.json(), strict=False)
            await dp.feed_update(bot, update)
            return web.Response()
        else:
            logger.warning("⚠️ Неверный токен в webhook")
            return web.Response(status=403)
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return web.Response(status=500)


async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy", 
        "bot": "Bloom AI", 
        "version": "5.1 - Stats System"
    })


async def main():
    """Main функция"""
    try:
        logger.info("🚀 Запуск Bloom AI v5.1 (Stats System)...")
        
        await on_startup()
        
        if WEBHOOK_URL:
            # Webhook mode
            app = web.Application()
            app.router.add_post('/webhook', webhook_handler)
            app.router.add_get('/health', health_check)
            app.router.add_get('/', health_check)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', PORT)
            await site.start()
            
            logger.info(f"🚀 Bloom AI v5.1 запущен на порту {PORT}")
            logger.info(f"✅ Stats System активирована!")
            
            try:
                await asyncio.Future()
            except KeyboardInterrupt:
                logger.info("🛑 Остановка через KeyboardInterrupt")
            finally:
                await runner.cleanup()
                await on_shutdown()
        else:
            # Polling mode
            logger.info("🤖 Запуск в режиме polling")
            logger.info("⏳ Ожидание сообщений от пользователей...")
            try:
                await dp.start_polling(bot, drop_pending_updates=True)
            except KeyboardInterrupt:
                logger.info("🛑 Остановка через KeyboardInterrupt")
            finally:
                await on_shutdown()
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}", exc_info=True)
