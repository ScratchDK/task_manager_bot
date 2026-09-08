from celery import shared_task
from datetime import datetime, timedelta
from app.core.database import SyncSessionLocal
from app.models.task import Task, TaskStatusEnum
from app.models.user import User
from app.bot.dispatcher import bot
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_deadlines():
    """Проверяет задачи с истекшим сроком выполнения."""
    with SyncSessionLocal() as db:
        overdue_tasks = db.query(Task).filter(
            Task.due_date < datetime.now(),
            Task.status.in_([TaskStatusEnum.pending, TaskStatusEnum.in_progress])
        ).all()

        if not overdue_tasks:
            logger.info("Нет задач с истекшим сроком выполнения")
            return

        for task in overdue_tasks:
            # Уведомляем создателя
            creator = db.get(User, task.created_by_id)
            if creator:
                try:
                    bot.send_message(
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
                assignee = db.get(User, task.assignee_id)
                if assignee:
                    try:
                        bot.send_message(
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

            task.status = TaskStatusEnum.cancelled
            db.commit()

        logger.info(f"Уведомления отправлены для {len(overdue_tasks)} просроченных задач")


@shared_task
def check_inactive_assignees():
    """Проверяет задачи с неактивными исполнителями."""
    with SyncSessionLocal() as db:
        tasks = db.query(Task).filter(
            Task.assignee_id != Task.created_by_id,
            Task.cancelled_by_inactivity == False,
            Task.due_date > datetime.now()
        ).all()

        for task in tasks:
            assignee = db.get(User, task.assignee_id)
            if not assignee:
                continue

            if assignee.is_active:
                # Исполнитель активирован - отправляем уведомление
                try:
                    bot.send_message(
                        chat_id=assignee.telegram_chat_id,
                        text=(
                            f"📩 Вам назначена задача!\n\n"
                            f"📝 {task.title}\n"
                            f"📄 {task.description or 'Без описания'}\n"
                            f"🚨 Приоритет: {task.priority}\n"
                            f"📅 Срок: {task.due_date.strftime('%d.%m.%Y') if task.due_date else 'не установлен'}\n"
                            f"👤 Назначил задачу: {task.created_by.username or task.created_by.telegram_chat_id}"
                        )
                    )
                    db.commit()
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение пользователю {assignee.telegram_chat_id}: {e}")

            else:
                days_passed = (datetime.now() - task.created_at).days

                if days_passed >= 3:
                    task.cancelled_by_inactivity = True
                    task.status = TaskStatusEnum.cancelled
                    task.completed_at = datetime.now()
                    db.commit()

                    creator = db.get(User, task.created_by_id)
                    if creator:
                        try:
                            bot.send_message(
                                chat_id=creator.telegram_chat_id,
                                text=(
                                    f"❌ Задача отменена из-за не активности исполнителя.\n\n"
                                    f"📝 {task.title}\n"
                                    f"📅 Создана: {task.created_at.strftime('%d.%m.%Y')}\n"
                                    f"👤 Исполнитель: {assignee.username or assignee.first_name}\n\n"
                                    f"Вы можете назначить другого исполнителя."
                                )
                            )
                        except Exception as e:
                            logger.error(f"Не удалось отправить сообщение пользователю {creator.telegram_chat_id}: {e}")
                else:
                    if task.notification_attempts % 24 == 0:
                        creator = db.get(User, task.created_by_id)
                        if creator:
                            try:
                                bot.send_message(
                                    chat_id=creator.telegram_chat_id,
                                    text=(
                                        f"⚠️ Напоминание: исполнитель @{assignee.username or assignee.first_name} "
                                        f"всё ещё не активировал бота.\n\n"
                                        f"📝 {task.title}\n"
                                        f"📅 Создана: {task.created_at.strftime('%d.%m.%Y')}\n\n"
                                        f"Если исполнитель не активирует бота в течение 3 дней, задача будет отменена."
                                    )
                                )
                            except Exception as e:
                                logger.error(
                                    f"Не удалось отправить сообщение пользователю {creator.telegram_chat_id}: {e}")

                    task.notification_attempts += 1
                    db.commit()


@shared_task
def check_upcoming_deadlines():
    """Проверяет задачи, до дедлайна которых осталось меньше часа."""
    with SyncSessionLocal() as db:
        now = datetime.now()
        in_one_hour = now + timedelta(hours=1)

        tasks = db.query(Task).filter(
            Task.due_date > now,
            Task.due_date <= in_one_hour,
            Task.status.in_([TaskStatusEnum.pending, TaskStatusEnum.in_progress])
        ).all()

        for task in tasks:
            assignee = db.get(User, task.assignee_id)
            if not assignee:
                continue

            creator_name = task.created_by.username or str(task.created_by.telegram_chat_id)

            text = (
                f"⏰ Напоминание! До дедлайна задачи остался 1 час!\n\n"
                f"📝 {task.title}\n"
                f"📄 {task.description or 'Без описания'}\n"
                f"📅 Срок: {task.due_date.strftime('%d.%m.%Y %H:%M')}"
            )

            if assignee.id != task.created_by_id:
                text += f"\n👤 Назначил задачу: {creator_name}"

            try:
                bot.send_message(
                    chat_id=assignee.telegram_chat_id,
                    text=text
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {assignee.telegram_chat_id}: {e}")

        logger.info(f"Уведомления о скором дедлайне отправлены для {len(tasks)} задач")

# TODO: На будущее для очистки старых задач и отдельного отображения архивных
@shared_task
def archive_old_tasks():
    """Архивирует задачи, завершённые более 30 дней назад."""
    with SyncSessionLocal() as db:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        old_tasks = db.query(Task).filter(
            Task.completed_at < thirty_days_ago
        ).all()

        for task in old_tasks:
            task.status = TaskStatusEnum.archived
            db.commit()
