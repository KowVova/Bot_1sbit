import os

from dotenv import load_dotenv

import logging
from logging.handlers import RotatingFileHandler

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
    )
from telegram.ext import (
    CommandHandler,
    Updater,
    Filters,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler
    )

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='LogBot.log',
    filemode='a'
    )
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('LogBot.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

load_dotenv()

MY_CHAT = os.getenv('MY_CHAT')
DIMA_CHAT = os.getenv('DIMA_CHAT')

secret_token = os.getenv('TOKEN')
chats = {
    'test': os.getenv('TEST_CHAT'),
    'manager_chat': os.getenv('MANAGER_CHAT'),
    'cto_chat':  os.getenv('CTO_CHAT'),
    'program_chat': os.getenv('PROGRAM_CHAT'),
    }

FIRST, SECOND = range(2)
order_dict = {}


def reset_order(client_id):
    ''' Очищает заявку'''
    order_dict[client_id] = {
        'inn': '',
        'tel': '',
        'text': '',
        'chat': '',
        'status': False}


def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def wake_up(update, context):
    """Вызывается по команде `/start`."""

    chat = update.effective_chat
    logger.info('Пользователь %s начал разговор', chat.first_name)
    reset_order(chat.id)
    reply_markup = start_menu()
    mes_text = (f'Привет {chat.first_name} ! \n'
                'Чем мы можем вам помочь?')
    context.bot.send_message(chat_id=chat.id, text=mes_text)
    context.bot.send_message(chat_id=chat.id,
                             text='Какой раздел Вас интересует ?',
                             reply_markup=reply_markup
                             )
    return FIRST


def wake_up_over(update, _):
    """ Тот же текст и клавиатура, что и при
         `/start`, но не как новое сообщение """

    query = update.callback_query
    query.answer()
    reset_order(update.effective_chat.id)
    reply_markup = start_menu()
    query.edit_message_text(
        text='Какой раздел Вас интересует ?', reply_markup=reply_markup
        )
    return FIRST


def text_processing(update, context):

    chat = update.effective_chat
    if update.message.text == 'привет бот':
        context.bot.send_message(chat_id=chat.id, text=chat.id,)
        return
    for cur_chat in chats.values():
        if str(chat.id) == cur_chat:
            return
    if not order_dict.get(chat.id):
        context.bot.send_message(
            chat_id=chat.id, text='Введите пожалуйста: "/start"'
            )
        return
    if order_dict[chat.id].get('status'):
        fill_order(update, context)
    else:
        new_talking(update, context)


def new_talking(update, context):
    chat = update.effective_chat
    keyboard = [[
            InlineKeyboardButton('Да', callback_data='another_question'),
            InlineKeyboardButton('Нет', callback_data='exit'),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mes_text = 'Хотите оформить новую заяку ?'
    context.bot.send_message(
            chat_id=chat.id,
            text=mes_text,
            reply_markup=reply_markup
            )
    return FIRST


def start_menu():
    ''' создает старовое меню общения'''
    button_list = [
        InlineKeyboardButton('Новая покупка', callback_data='buy_dev'),
        InlineKeyboardButton(
            'Не работает оборудование',
            callback_data='cto_order'
            ),
        InlineKeyboardButton(
            'Нужна помощь программиста',
            callback_data='programming'
            ),
        InlineKeyboardButton('Выход', callback_data='exit'),
        ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    return reply_markup


def buy_dev(update, _):
    """Активация приема заявки для менеджеров"""

    chat = update.effective_chat
    order_dict[chat.id]['chat'] = chats['manager_chat']
    order_dict[chat.id]['status'] = True
    new_order(update)


def cto_order(update, _):
    """Активация приема заявки для ЦТО"""

    chat = update.effective_chat
    order_dict[chat.id]['chat'] = chats['cto_chat']
    order_dict[chat.id]['status'] = True
    new_order(update)


def programming(update, _):
    """Активация приема заявки для программистов"""

    chat = update.effective_chat
    order_dict[chat.id]['chat'] = chats['program_chat']
    order_dict[chat.id]['status'] = True
    new_order(update)


def new_order(update):
    '''Начало заполнения новой заявки'''
    query = update.callback_query
    query.answer()
    message_text = 'Введите пожалуйста Название Компании'
    keyboard = [
        [
            InlineKeyboardButton('Отмена', callback_data='another_question'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=message_text, reply_markup=reply_markup)
    return FIRST


def fill_order(update, context):
    """Заполнение новой заявки"""

    chat = update.effective_chat
    if order_dict[chat.id]['inn'] == '':
        order_dict[chat.id]['inn'] = update.message.text
        message_text = 'Укажите Ваш телефон для связи'
        keyboard = [
            [
               InlineKeyboardButton('Назад', callback_data='another_question'),
            ]
        ]
    elif order_dict[chat.id]['tel'] == '':
        order_dict[chat.id]['tel'] = update.message.text
        if order_dict[chat.id]['chat'] == chats['manager_chat']:
            message_text = 'Что Вы хотите приобрести?'
        else:
            message_text = 'Опишите ваш вопрос'
        keyboard = [
            [
                InlineKeyboardButton(
                    'Назад',
                    callback_data='another_question'
                    ),
            ]
        ]
    elif order_dict[chat.id]['text'] == '':
        order_dict[chat.id]['text'] = update.message.text
        message_text = 'Проверьте заявку и нажмите отправить'
        inn, tel, text_order, *z = order_dict[chat.id].values()
        mes_text = (f'Компания: {inn}\n тел: {tel} {chat.first_name}\n'
                    f'Описание вопроса: {text_order}')
        logger.info(f'Cоставлена заявка:\n {mes_text}')
        context.bot.send_message(chat_id=chat.id, text=mes_text)
        keyboard = [
            [
                InlineKeyboardButton('Отправить', callback_data='send_order'),
                InlineKeyboardButton('Назад', callback_data='another_question')
            ]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat.id,
                             text=message_text,
                             reply_markup=reply_markup
                             )
    return FIRST


def send_order(update, context):
    chat = update.effective_chat
    inn, tel, text_order, g_chat, *z = order_dict[chat.id].values()
    mes_text = (f'Заявка отправлена в чат {g_chat}:\n'
                f'Компания: {inn}\n тел: {tel} {chat.first_name}\n'
                f'Описание вопроса: {text_order}')
    if str(chat.id) == MY_CHAT:
        address_chat = MY_CHAT
    elif str(chat.id) == DIMA_CHAT:
        address_chat = DIMA_CHAT
    else:
        address_chat = chats['test']
    context.bot.send_message(chat_id=address_chat, text=mes_text)
    reset_order(chat.id)
    new_talking(update, context)


def next_level(update, _):
    """Показ выбора кнопок"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton(
                'Да, есть еще вопрос !',
                callback_data='another_question'
                ),
            InlineKeyboardButton(
                'Нет, с меня хватит ...',
                callback_data='exit'
                ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text='Продолжим общение ?', reply_markup=reply_markup
    )
    # Переход в состояние разговора `SECOND`
    return SECOND


def end(update, _):
    """Возвращает `ConversationHandler.END`, который говорит
    `ConversationHandler` что разговор окончен"""
    chat = update.effective_chat
    query = update.callback_query
    query.answer()
    msg = f'До свидания, {chat.first_name} ! \nБуду ждать Вас здесь снова :)'
    button = ReplyKeyboardMarkup(
        [['- Начать разговор -']],
        resize_keyboard=True
        )
    query.edit_message_text(text=msg)
    bot.send_message(
        chat_id=chat.id,
        text='',
        reply_markup=button
    )
    return ConversationHandler.END


def button(update, _):
    query = update.callback_query

    query.answer()
    msg = 'Для составления заявки ответьте пожалуйста на ряд вопросов'
    query.edit_message_text(text=msg)


def help_command(update, _):
    update.message.reply_text("Используйте `/start` для тестирования.")


if __name__ == '__main__':

    bot = Bot(token=secret_token)
    updater = Updater(token=secret_token)

    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', wake_up)],
        states={
            FIRST: [
                CallbackQueryHandler(
                    buy_dev,
                    pattern='^' + 'buy_dev' + '$'
                    ),
                CallbackQueryHandler(
                    cto_order,
                    pattern='^' + 'cto_order' + '$'
                    ),
                CallbackQueryHandler(
                    next_level,
                    pattern='^' + 'next_level' + '$'
                    ),
                CallbackQueryHandler(
                    programming,
                    pattern='^' + 'programming' + '$'
                    ),
                CallbackQueryHandler(
                    send_order,
                    pattern='^' + 'send_order' + '$'
                    ),
                CallbackQueryHandler(
                    end,
                    pattern='^' + 'exit' + '$'),
                CallbackQueryHandler(
                    wake_up_over,
                    pattern='^' + 'another_question' + '$'
                    ),
            ],
            SECOND: [
                CallbackQueryHandler(
                    wake_up_over,
                    pattern='^' + 'another_question' + '$'
                    ),
                CallbackQueryHandler(end, pattern='^' + 'exit' + '$'),
            ],
        },
        fallbacks=[CommandHandler('start', wake_up)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(MessageHandler(Filters.text, text_processing))

    updater.start_polling()
    updater.idle()
