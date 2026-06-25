from __future__ import annotations

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import address_confirm_keyboard, addresses_keyboard, broadcast_confirm_keyboard
from app.bot.states import AddAddress, BroadcastFlow
from app.db import repositories as repo
from app.db.models import Broadcast
from app.domain import AddressConfidence
from app.matching.address import parse_user_address
from app.services.container import AppContainer
from app.services.messages import format_address_confirmation, format_history_item
from app.services.sync import SyncService

user_router = Router(name="user")
admin_router = Router(name="admin")


def include_routers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(admin_router)
    dispatcher.include_router(user_router)


def _is_admin(container: AppContainer, telegram_id: int) -> bool:
    return telegram_id in container.settings.admin_ids


@user_router.message(Command("start"))
async def start(message: Message, state: FSMContext, container: AppContainer) -> None:
    async with container.session_factory() as session:
        await repo.upsert_user(
            session,
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
        )
        await session.commit()
    await state.set_state(AddAddress.waiting_for_title)
    await message.answer(
        "Привет. Я буду присылать уведомления о плановых отключениях.\n\n"
        "Как назвать первый адрес? Например: Дом, Работа, Родители."
    )


@user_router.message(Command("add_address"))
async def add_address(message: Message, state: FSMContext) -> None:
    await state.set_state(AddAddress.waiting_for_title)
    await message.answer("Как назвать адрес? Например: Дом, Работа, Родители.")


@user_router.message(AddAddress.waiting_for_title)
async def address_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Введите короткое название адреса.")
        return
    await state.update_data(address_title=title[:80])
    await state.set_state(AddAddress.waiting_for_address)
    await message.answer("Теперь отправьте адрес свободным текстом. Например: Грозный, ул. Мира")


@user_router.message(AddAddress.waiting_for_address)
async def address_text(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").strip()
    if not raw_text:
        await message.answer("Введите адрес текстом.")
        return
    parsed = parse_user_address(raw_text)
    await state.update_data(
        raw_text=raw_text,
        locality=parsed.locality,
        street=parsed.street,
        district=parsed.district,
        confidence=parsed.confidence.value,
    )
    await state.set_state(AddAddress.waiting_for_confirmation)
    await message.answer(
        format_address_confirmation(
            None,
            raw_text,
            {
                "locality": parsed.locality,
                "street": parsed.street,
                "confidence": parsed.confidence.value,
            },
        ),
        reply_markup=address_confirm_keyboard(),
    )


@user_router.callback_query(AddAddress.waiting_for_confirmation, F.data == "address:retry")
async def retry_address(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddAddress.waiting_for_address)
    await callback.message.answer("Хорошо, отправьте адрес заново.")
    await callback.answer()


@user_router.callback_query(AddAddress.waiting_for_confirmation, F.data == "address:confirm")
async def confirm_address(
    callback: CallbackQuery,
    state: FSMContext,
    container: AppContainer,
) -> None:
    data = await state.get_data()
    async with container.session_factory() as session:
        user = await repo.upsert_user(
            session,
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            username=callback.from_user.username,
        )
        address = await repo.add_user_address(
            session,
            user=user,
            title=data["address_title"],
            raw_text=data["raw_text"],
        )
        await session.commit()
    await state.clear()
    await callback.message.answer(f"Адрес сохранен: {address.title}")
    sync_service = SyncService(
        settings=container.settings,
        session_factory=container.session_factory,
        bot=container.bot,
    )
    sent = await sync_service.notify_known_segments_for_user(callback.from_user.id)
    if sent:
        await callback.message.answer(f"Нашел уже известные отключения по этому адресу: {sent}.")
    await callback.answer()


@user_router.message(Command("addresses"))
async def addresses(message: Message, container: AppContainer) -> None:
    async with container.session_factory() as session:
        items = await repo.list_user_addresses(session, message.from_user.id)
    if not items:
        await message.answer("Адресов пока нет. Добавьте первый через /add_address.")
        return
    lines = ["Ваши адреса:"]
    for item in items:
        confidence = AddressConfidence(item.confidence)
        lines.append(f"#{item.id} {item.title}: {item.raw_text} ({confidence.value})")
    await message.answer(
        "\n".join(lines),
        reply_markup=addresses_keyboard([item.id for item in items]),
    )


@user_router.callback_query(F.data.startswith("address:delete:"))
async def delete_address(callback: CallbackQuery, container: AppContainer) -> None:
    address_id = int(callback.data.rsplit(":", 1)[1])
    async with container.session_factory() as session:
        deleted = await repo.delete_user_address(session, callback.from_user.id, address_id)
        await session.commit()
    await callback.answer("Удалено" if deleted else "Адрес не найден")
    await callback.message.answer("Адрес удален." if deleted else "Адрес не найден.")


@user_router.message(Command("history"))
async def history(message: Message, container: AppContainer) -> None:
    async with container.session_factory() as session:
        items = await repo.user_history(session, message.from_user.id)
    if not items:
        await message.answer("Истории уведомлений пока нет.")
        return
    await message.answer("Последние уведомления:\n" + "\n".join(format_history_item(item) for item in items))


@user_router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "/addresses - мои адреса\n"
        "/add_address - добавить адрес\n"
        "/history - последние уведомления\n"
        "/delete_me - удалить мои данные"
    )


@user_router.message(Command("delete_me"))
async def delete_me(message: Message, container: AppContainer) -> None:
    async with container.session_factory() as session:
        deleted = await repo.delete_user(session, message.from_user.id)
        await session.commit()
    await message.answer("Ваши данные удалены." if deleted else "Данных для удаления не найдено.")


@admin_router.message(Command("sync"))
async def sync(message: Message, container: AppContainer) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    result = await SyncService(
        settings=container.settings,
        session_factory=container.session_factory,
        bot=container.bot,
    ).sync(dry_run=False)
    await message.answer(_format_sync_result(result))


@admin_router.message(Command("sync_dry_run"))
async def sync_dry_run(message: Message, container: AppContainer) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    result = await SyncService(
        settings=container.settings,
        session_factory=container.session_factory,
        bot=container.bot,
    ).sync(dry_run=True)
    await message.answer(_format_sync_result(result))


@admin_router.message(Command("latest"))
async def latest(message: Message, container: AppContainer) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    async with container.session_factory() as session:
        outages = await repo.latest_outages(session)
    if not outages:
        await message.answer("Отключений пока нет.")
        return
    await message.answer(
        "Последние отключения:\n"
        + "\n".join(f"{item.event_date:%d.%m.%Y} {item.title} #{item.external_id}" for item in outages)
    )


@admin_router.message(Command("stats"))
async def stats(message: Message, container: AppContainer) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    async with container.session_factory() as session:
        values = await repo.stats(session)
    await message.answer("\n".join(f"{key}: {value}" for key, value in values.items()))


@admin_router.message(Command("sources"))
async def sources(message: Message, container: AppContainer) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    async with container.session_factory() as session:
        check = await repo.last_source_check(session)
    if check is None:
        await message.answer("Проверок источника еще не было.")
        return
    last_success = f"{check.last_success_at:%d.%m.%Y %H:%M}" if check.last_success_at else "нет"
    await message.answer(
        "Статус источника:\n"
        f"Статус: {check.status}\n"
        f"Проверка: {check.checked_at:%d.%m.%Y %H:%M}\n"
        f"Последний успех: {last_success}\n"
        f"Ошибок подряд: {check.consecutive_errors}\n"
        f"Ошибка: {check.error_message or '-'}"
    )


@admin_router.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext, container: AppContainer) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    await state.set_state(BroadcastFlow.waiting_for_text)
    await message.answer("Отправьте текст рассылки.")


@admin_router.message(BroadcastFlow.waiting_for_text)
async def broadcast_preview(
    message: Message,
    state: FSMContext,
    container: AppContainer,
) -> None:
    if not _is_admin(container, message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст рассылки пустой.")
        return
    async with container.session_factory() as session:
        broadcast = await repo.create_broadcast(session, message.from_user.id, text)
        await session.commit()
    await state.clear()
    await message.answer(
        f"Preview рассылки #{broadcast.id}:\n\n{text}",
        reply_markup=broadcast_confirm_keyboard(broadcast.id),
    )


@admin_router.callback_query(F.data.startswith("broadcast:cancel:"))
async def broadcast_cancel(callback: CallbackQuery, container: AppContainer) -> None:
    if not _is_admin(container, callback.from_user.id):
        return
    broadcast_id = int(callback.data.rsplit(":", 1)[1])
    async with container.session_factory() as session:
        broadcast = await session.get(Broadcast, broadcast_id)
        if broadcast:
            broadcast.status = "cancelled"
        await session.commit()
    await callback.answer("Отменено")
    await callback.message.answer("Рассылка отменена.")


@admin_router.callback_query(F.data.startswith("broadcast:send:"))
async def broadcast_send(callback: CallbackQuery, container: AppContainer) -> None:
    if not _is_admin(container, callback.from_user.id):
        return
    broadcast_id = int(callback.data.rsplit(":", 1)[1])
    async with container.session_factory() as session:
        broadcast = await session.get(Broadcast, broadcast_id)
        if broadcast is None or broadcast.status != "draft":
            await callback.answer("Рассылка не найдена или уже обработана")
            return
        users = await repo.get_all_active_users(session)
        sent = 0
        for user in users:
            await container.bot.send_message(user.telegram_id, broadcast.text)
            sent += 1
        broadcast.status = "sent"
        broadcast.sent_count = sent
        await session.commit()
    await callback.answer("Отправлено")
    await callback.message.answer(f"Рассылка отправлена. Получателей: {sent}")


def _format_sync_result(result) -> str:
    if result.error:
        return f"Sync failed: {result.error}"
    prefix = "Dry run" if result.dry_run else "Sync"
    return (
        f"{prefix} completed\n"
        f"Events: {result.events_found}\n"
        f"Segments: {result.segments_found}\n"
        f"Potential/sent notifications: {result.notifications_sent}"
    )
