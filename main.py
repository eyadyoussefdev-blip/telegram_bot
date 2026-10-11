import asyncio
import requests
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# توكن البوت الخاص بك في تيليجرام
BOT_TOKEN = "8925059586:AAHHpZ9JN3ULQPfSUWEMrie-pvF-PJsqmcE"

# إعدادات Cloudflare D1 الخاصة بك
CLOUDFLARE_ACCOUNT_ID = "0e5c152af7b0da7b498f927ac334b9cc"
CLOUDFLARE_DATABASE_ID = "97ce6ff7-6f0c-46fd-8584-095abd500ef2"
CLOUDFLARE_API_TOKEN = "cfut_oXLTZs5GqR67t0iFRUhG07M2mpHRDk678Blgi28443654165"

# 🔑 كلمة السر للوصول للبوت
ADMIN_PASSWORD = "123"

# قائمة المستخدمين الموثقين
authorized_users = set()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def execute_d1_query(sql_query: str, params: list = None):
    """
    دالة عامة للاتصال وتنفيذ الاستعلامات في Cloudflare D1 REST API
    """
    if params is None:
        params = []

    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query"
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "sql": sql_query,
        "params": params
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        res_data = response.json()
        if res_data.get("success"):
            results = res_data.get("result", [])
            if results and len(results) > 0:
                return results[0].get("results", [])
    return []


# --- أوامر البوت ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    if user_id in authorized_users:
        await message.answer(
            "أهلاً بك مجدداً! البوت جاهز للاستخدام.\n\n"
            "📌 **الأوامر المتاحة:**\n"
            "• `/search الاسم أو الـ ID` (للبحث الشامل)\n"
            "• `/count > 100` (لحساب النقاط)\n"
            "• `/logout` (لتسجيل الخروج)",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🔒 **البوت محمي بكلمة سر.**\n\n"
            "للسلامة، سيقوم البوت بحذف رسالة كلمة السر فور إرسالها تلقائياً.\n"
            "اكتب الأمر هكذا:\n"
            "`/login كلمة_السر`",
            parse_mode="Markdown"
        )


@dp.message(Command("login"))
async def login_handler(message: Message):
    """تسجيل الدخول مع حذف رسالة كلمة السر تلقائياً لحمايتك"""
    user_id = message.from_user.id
    
    # حذف رسالة المستخدم التي تحتوي على كلمة السر فوراً
    try:
        await message.delete()
    except Exception:
        pass

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        temp_msg = await message.answer("⚠️ يرجى كتابة كلمة السر هكذا: `/login كلمة_السر`", parse_mode="Markdown")
        await asyncio.sleep(5)
        try:
            await temp_msg.delete()
        except Exception:
            pass
        return

    password = args[1].strip()
    if password == ADMIN_PASSWORD:
        authorized_users.add(user_id)
        success_msg = await message.answer(
            "✅ **تم تسجيل الدخول بنجاح!**\nتم مسح كلمة السر من الدردشة لأمانك.\n"
            "يمكنك الآن استخدام الأوامر (`/search` أو `/count`).",
            parse_mode="Markdown"
        )
        await asyncio.sleep(6)
        try:
            await success_msg.delete()
        except Exception:
            pass
    else:
        fail_msg = await message.answer("❌ كلمة السر غير صحيحة!")
        await asyncio.sleep(4)
        try:
            await fail_msg.delete()
        except Exception:
            pass


@dp.message(Command("logout"))
async def logout_handler(message: Message):
    """تسجيل الخروج وقفل البوت"""
    user_id = message.from_user.id
    try:
        await message.delete()
    except Exception:
        pass

    if user_id in authorized_users:
        authorized_users.remove(user_id)
        msg = await message.answer("🔒 **تم تسجيل الخروج بنجاح ومسح الجلسة.**", parse_mode="Markdown")
    else:
        msg = await message.answer("⚠️ أنت غير مسجل الدخول بالفعل.")
    
    await asyncio.sleep(4)
    try:
        await msg.delete()
    except Exception:
        pass


@dp.message(Command("search"))
async def search_handler(message: Message):
    """البحث المدمج: يبحث في userId أو userName في نفس الوقت"""
    if message.from_user.id not in authorized_users:
        await message.answer("🔒 عذراً، يجب عليك تسجيل الدخول أولاً باستخدام `/login كلمة_السر`", parse_mode="Markdown")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ يرجى كتابة الـ ID أو اسم المستخدم للبحث، مثال:\n`/search XQM2FN` أو `/search أحمد`", parse_mode="Markdown")
        return

    query_value = args[1].strip()
    await message.answer(f"⏳ جاري البحث عن: `{query_value}` ...", parse_mode="Markdown")

    try:
        sql_query = "SELECT userId, userName, points, uc, isBanned FROM users WHERE userId = ? OR userName LIKE ?"
        data = execute_d1_query(sql_query, [query_value, f"%{query_value}%"])
        
        if not data:
            await message.answer("❌ لم يتم العثور على أي نتائج مطابقة.")
            return

        response = "📊 **النتائج المستخرجة:**\n\n"
        for row in data:
            response += (
                f"👤 **الاسم:** `{row.get('userName', 'N/A')}`\n"
                f"🆔 **ID:** `{row.get('userId', 'N/A')}`\n"
                f"⭐ **النقاط:** `{row.get('points', 0)}` | 💎 **UC:** `{row.get('uc', 0)}` | 🚫 **محظور:** `{row.get('isBanned', 0)}` \n"
                f"-----------------------------\n"
            )

        await message.answer(response, parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"⚠️ حدث خطأ أثناء الاتصال:\n`{e}`", parse_mode="Markdown")


@dp.message(Command("count"))
async def count_handler(message: Message):
    if message.from_user.id not in authorized_users:
        await message.answer("🔒 عذراً، يجب عليك تسجيل الدخول أولاً باستخدام `/login كلمة_السر`", parse_mode="Markdown")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "⚠️ طريقة الاستخدام غير صحيحة.\nمثال:\n`/count > 100`",
            parse_mode="Markdown"
        )
        return

    operator = args[1]
    try:
        points_value = int(args[2])
    except ValueError:
        await message.answer("⚠️ يرجى كتابة رقم صحيح للنقاط، مثال: `/count > 50`", parse_mode="Markdown")
        return

    if operator not in ['=', '>', '<', '>=', '<=', '!=']:
        await message.answer("⚠️ المعامل المستخدم غير صالح.", parse_mode="Markdown")
        return

    await message.answer(f"⏳ جاري الحساب...", parse_mode="Markdown")

    try:
        sql_query = f"SELECT COUNT(*) as total FROM users WHERE points {operator} ?"
        res = execute_d1_query(sql_query, [points_value])
        
        total_count = 0
        if res and len(res) > 0:
            total_count = res[0].get("total", 0)

        await message.answer(
            f"📊 **النتيجة:**\nعدد المستخدمين: **{total_count}** مستخدم.",
            parse_mode="Markdown"
        )

    except Exception as e:
        await message.answer(f"⚠️ حدث خطأ:\n`{e}`", parse_mode="Markdown")


async def main():
    print("البوت يعمل الآن مع خاصية الحذف التلقائي لرسائل تسجيل الدخول...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())