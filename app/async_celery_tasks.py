from celery import shared_task
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.models.task import Task, TaskStatusEnum
from app.models.user import User
from app.bot.dispatcher import bot
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_deadlines():
    """
    Проверяет задачи с истекшим сроком выполнения и отправляет уведомления.
    Запускается по расписанию (каждый час).
    """
    # ❗ ВАЖНО: Celery не умеет работать с asyncio напрямую. ❗
    # Поэтому использую asyncio.run() для запуска асинхронной функции.
    import asyncio
    asyncio.run(_check_deadlines_async())


async def _check_deadlines_async():
    """Асинхронная логика проверки дедлайнов."""
    async with AsyncSessionLocal() as db:
        # Находим задачи, у которых дедлайн прошел, а статус не completed/cancelled
        query = select(Task).where(
            Task.due_date < datetime.now(),
            Task.status.in_([TaskStatusEnum.pending, TaskStatusEnum.in_progress])
        )
        result = await db.execute(query)
        overdue_tasks = result.scalars().all()

        if not overdue_tasks:
            logger.info("Нет задач с истекшим сроком выполнения")
            return

        for task in overdue_tasks:
            # Уведомляем создателя
            creator = await db.get(User, task.created_by_id)
            if creator:
                try:
                    await bot.send_message(
                        chat_id=creator.telegram_chat_id,
                        text=(
                            f"⚠️ Истек срок выполнения задачи:\n"
                            f"📝 {task.title}\n"
                            f"📅 Срок: {task.due_date.strftime('%d.%m.%Y')}\n"
                            f"🆔 ID: {task.id}"
                        )
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить создателя {creator.id}: {e}")

            # Уведомляем исполнителя (если он не создатель)
            if task.assignee_id and task.assignee_id != task.created_by_id:
                assignee = await db.get(User, task.assignee_id)
                if assignee:
                    try:
                        await bot.send_message(
                            chat_id=assignee.telegram_chat_id,
                            text=(
                                f"⚠️ Истек срок выполнения задачи:\n"
                                f"📝 {task.title}\n"
                                f"📅 Срок: {task.due_date.strftime('%d.%m.%Y')}\n"
                                f"🆔 ID: {task.id}\n"
                                f"👤 Назначил задачу: {task.created_by.username or task.created_by.telegram_chat_id}"
                            )
                        )
                    except Exception as e:
                        logger.error(f"Не удалось уведомить исполнителя {assignee.id}: {e}")
        logger.info(f"Уведомления отправлены для {len(overdue_tasks)} просроченных задач")


@shared_task
def check_inactive_assignees():
    """
    Проверяет задачи, где исполнитель не активен.
    Отправляет повторные уведомления или отменяет задачу через 3 дня.
    """
    import asyncio
    asyncio.run(_check_inactive_assignees_async())


async def _check_inactive_assignees_async():
    async with AsyncSessionLocal() as db:
        # Проверяем задачи, где:
        # 1 есть исполнитель (не создатель)
        # 2 не отменена из-за того что пользователь не активировал бот
        # 3 дедлайн ещё не наступил
        query = select(Task).where(
            Task.assignee_id != Task.created_by_id,
            Task.cancelled_by_inactivity == False,
            Task.due_date > datetime.now()
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        for task in tasks:
            assignee = await db.get(User, task.assignee_id)
            if not assignee:
                continue

            # Проверяем, активен ли исполнитель
            if assignee.is_active:
                # Исполнитель активировался — отправляем уведомление
                await bot.send_message(
                    chat_id=assignee.telegram_chat_id,
                    text=(
                        f"📩 Вам назначена задача!\n\n"
                        f"📝 {task.title}\n"
                        f"📄 {task.description or 'Без описания'}\n"
                        f"🚨 Приоритет: {task.priority}\n"
                        f"📅 Срок: {task.due_date.strftime('%d.%m.%Y') if task.due_date else 'не установлен'}"
                        f"👤 Назначил задачу: {task.created_by.username or task.created_by.telegram_chat_id}"
                    )
                )
                # Помечаем, что уведомление отправлено
                task.last_notification_sent = datetime.now()
                task.notification_attempts += 1
                await db.commit()
            else:
                # ❌ Исполнитель всё ещё не активен
                # Проверяем, сколько прошло времени с момента создания
                days_passed = (datetime.now() - task.created_at).days

                if days_passed >= 3:
                    # Прошло 3 дня — отменяем задачу
                    task.cancelled_by_inactivity = True
                    task.status = TaskStatusEnum.cancelled
                    await db.commit()

                    # Уведомляем создателя
                    creator = await db.get(User, task.created_by_id)
                    if creator:
                        await bot.send_message(
                            chat_id=creator.telegram_chat_id,
                            text=(
                                f"❌ Задача отменена из-за неактивности исполнителя.\n\n"
                                f"📝 {task.title}\n"
                                f"📅 Создана: {task.created_at.strftime('%d.%m.%Y')}\n"
                                f"👤 Исполнитель: {assignee.username or assignee.first_name}\n\n"
                                f"Вы можете назначить другого исполнителя."
                            )
                        )
                else:
                    if task.notification_attempts % 24 == 0:  # Раз в день уведомляем создателя задачи
                        creator = await db.get(User, task.created_by_id)
                        if creator:
                            await bot.send_message(
                                chat_id=creator.telegram_chat_id,
                                text=(
                                    f"⚠️ Напоминание: исполнитель @{assignee.username or assignee.first_name} "
                                    f"всё ещё не активировал бота.\n\n"
                                    f"📝 {task.title}\n"
                                    f"📅 Создана: {task.created_at.strftime('%d.%m.%Y')}\n\n"
                                    f"Если исполнитель не активирует бота в течение 3 дней, задача будет отменена."
                                )
                            )

                    task.notification_attempts += 1
                    await db.commit()


@shared_task
def check_upcoming_deadlines():
    """
    Проверяет задачи, до дедлайна которых осталось меньше часа.
    Отправляет уведомление исполнителю.
    """
    import asyncio
    asyncio.run(_check_upcoming_deadlines_async())


async def _check_upcoming_deadlines_async():
    async with AsyncSessionLocal() as db:
        now = datetime.now()
        in_one_hour = now + timedelta(hours=1)

        query = select(Task).where(
            Task.due_date > now,
            Task.due_date <= in_one_hour,
            Task.status.in_([TaskStatusEnum.pending, TaskStatusEnum.in_progress])
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        for task in tasks:
            assignee = await db.get(User, task.assignee_id)
            if not assignee:
                continue  # На всякий случай, assignee есть всегда, но вдруг

            creator_name = task.created_by.username or str(task.created_by.telegram_chat_id)

            text = (
                f"⏰ Напоминание! До дедлайна задачи остался 1 час!\n\n"
                f"📝 {task.title}\n"
                f"📄 {task.description or 'Без описания'}\n"
                f"📅 Срок: {task.due_date.strftime('%d.%m.%Y %H:%M')}"
            )

            # Добавляем создателя, если это не сам пользователь
            if assignee.id != task.created_by_id:
                text += f"\n👤 Назначил задачу: {creator_name}"

            await bot.send_message(
                chat_id=assignee.telegram_chat_id,
                text=text
            )

        logger.info(f"Уведомления о скором дедлайне отправлены для {len(tasks)} задач")
